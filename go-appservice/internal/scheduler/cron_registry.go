package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
	"github.com/riverqueue/river/rivertype"
	"github.com/robfig/cron/v3"
)

// CronRegistry holds the live mapping between scheduler.scheduled_tasks
// rows and River PeriodicJob handles so we can add/remove on
// pg_notify events without restarting the River client.
type CronRegistry struct {
	mu      sync.Mutex
	handles map[string]rivertype.PeriodicJobHandle // task_id → handle
	client  periodicAdder
	store   *PgStore
	parser  cron.Parser
}

// periodicAdder is the subset of *river.Client we need. Kept as an
// interface so tests don't have to construct a real client.
type periodicAdder interface {
	PeriodicJobs() *river.PeriodicJobBundle
}

// NewCronRegistry constructs the registry. The caller is responsible for
// calling Reload() at startup and WatchNotifications() in a goroutine.
func NewCronRegistry(client periodicAdder, store *PgStore) *CronRegistry {
	return &CronRegistry{
		handles: make(map[string]rivertype.PeriodicJobHandle),
		client:  client,
		store:   store,
		parser: cron.NewParser(
			cron.Minute | cron.Hour | cron.Dom | cron.Month | cron.Dow,
		),
	}
}

// Reload discards all existing periodic jobs and re-reads scheduler.
// scheduled_tasks. Called at startup and after a fatal NOTIFY-reload
// error to recover a consistent view.
func (r *CronRegistry) Reload(ctx context.Context) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	// Clear existing handles.
	for taskID, handle := range r.handles {
		r.client.PeriodicJobs().Remove(handle)
		slog.Debug("scheduler: removed periodic job", "task_id", taskID)
	}
	r.handles = make(map[string]rivertype.PeriodicJobHandle)

	tasks, err := r.store.ListActiveTasks(ctx)
	if err != nil {
		return fmt.Errorf("list active tasks: %w", err)
	}

	for _, task := range tasks {
		if err := r.addLocked(task); err != nil {
			slog.Warn("scheduler: skipping task with invalid cron",
				"task_id", task.TaskID,
				"cron_expr", task.CronExpr,
				"error", err)
			continue
		}
	}
	slog.Info("scheduler: cron registry reloaded", "active_tasks", len(r.handles))
	return nil
}

// AddOrUpdate registers (or re-registers) one task. Used by the pg_notify
// watcher so individual row changes avoid a full Reload().
func (r *CronRegistry) AddOrUpdate(ctx context.Context, taskID string) error {
	task, err := r.store.LoadTask(ctx, taskID)
	if err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	// Remove any existing handle first so replace-semantics hold.
	if existing, ok := r.handles[taskID]; ok {
		r.client.PeriodicJobs().Remove(existing)
		delete(r.handles, taskID)
	}
	// Only active cron-kind tasks register periodic jobs. Others (paused,
	// cancelled, one_shot) are left alone — one_shot is handled via
	// River's ScheduledAt insert, future Phase-2 extension.
	if task.Status != "active" || task.CronExpr == "" {
		return nil
	}
	return r.addLocked(task)
}

// Remove deletes the periodic-job registration for taskID (no-op if absent).
func (r *CronRegistry) Remove(taskID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if handle, ok := r.handles[taskID]; ok {
		r.client.PeriodicJobs().Remove(handle)
		delete(r.handles, taskID)
	}
}

// addLocked is the shared add-path (mutex must be held).
//
// Timezone: robfig/cron's cron.Parser.Parse returns a SpecSchedule that
// evaluates in time.Local. For user-owned tasks we want the IANA tz
// column ("Europe/Zurich", "America/New_York") to drive firing — a user
// in Zurich saying "jeden Montag 9 Uhr" should fire at 09:00 Zurich,
// not 09:00 server-local. We wrap the parsed schedule in a locScheduler
// that shifts the evaluation to the task's location.
func (r *CronRegistry) addLocked(task *ScheduledTask) error {
	schedule, err := r.parser.Parse(task.CronExpr)
	if err != nil {
		return fmt.Errorf("parse cron %q: %w", task.CronExpr, err)
	}

	loc, locErr := loadTaskLocation(task.TZ)
	if locErr != nil {
		slog.Warn("scheduler: invalid tz, falling back to UTC",
			"task_id", task.TaskID, "tz", task.TZ, "error", locErr)
		loc = time.UTC
	}
	schedule = locScheduler{inner: schedule, loc: loc}

	// Bind taskID in closure to keep per-task identity.
	taskID := task.TaskID
	pj := river.NewPeriodicJob(
		schedule,
		func() (river.JobArgs, *river.InsertOpts) {
			return MatrixDispatchArgs{TaskID: taskID}, nil
		},
		&river.PeriodicJobOpts{},
	)
	handle := r.client.PeriodicJobs().Add(pj)
	r.handles[taskID] = handle
	slog.Info("scheduler: registered cron task",
		"task_id", taskID,
		"cron_expr", task.CronExpr,
		"tz", loc.String(),
		"kind", task.Kind)
	return nil
}

// locScheduler wraps a cron.Schedule so Next() is evaluated in a specific
// time.Location rather than time.Local. River calls Next(t time.Time);
// we convert to the target tz, let the inner schedule compute next fire
// in that tz, then return the resulting time in UTC.
type locScheduler struct {
	inner cron.Schedule
	loc   *time.Location
}

func (s locScheduler) Next(t time.Time) time.Time {
	return s.inner.Next(t.In(s.loc)).UTC()
}

func loadTaskLocation(tz string) (*time.Location, error) {
	if tz == "" {
		return time.UTC, nil
	}
	loc, err := time.LoadLocation(tz)
	if err != nil {
		return nil, fmt.Errorf("load tz %q: %w", tz, err)
	}
	return loc, nil
}

// WatchNotifications LISTENs on scheduler_task_changed (fired by the
// trg_scheduled_tasks_notify trigger in migration 019). For each
// notification it reloads the affected row into the registry. Runs until
// ctx is cancelled; returns ctx.Err() on normal shutdown.
func (r *CronRegistry) WatchNotifications(ctx context.Context, pool *pgxpool.Pool) error {
	conn, err := pool.Acquire(ctx)
	if err != nil {
		return fmt.Errorf("acquire listen conn: %w", err)
	}
	defer conn.Release()

	if _, err := conn.Exec(ctx, "LISTEN scheduler_task_changed"); err != nil {
		return fmt.Errorf("listen: %w", err)
	}
	slog.Info("scheduler: listening for task changes")

	for {
		notice, err := conn.Conn().WaitForNotification(ctx)
		if err != nil {
			if ctxErr := ctx.Err(); ctxErr != nil {
				return fmt.Errorf("scheduler watch cancelled: %w", ctxErr)
			}
			return fmt.Errorf("wait notification: %w", err)
		}
		r.handleNotification(ctx, notice)
	}
}

type notifyPayload struct {
	TaskID string `json:"task_id"`
	Op     string `json:"op"`
	Status string `json:"status"`
}

func (r *CronRegistry) handleNotification(ctx context.Context, notice *pgconn.Notification) {
	var payload notifyPayload
	if err := json.Unmarshal([]byte(notice.Payload), &payload); err != nil {
		slog.Warn("scheduler: unparseable NOTIFY payload",
			"channel", notice.Channel,
			"payload", notice.Payload,
			"error", err)
		return
	}
	switch payload.Op {
	case "DELETE":
		r.Remove(payload.TaskID)
		slog.Info("scheduler: task removed via NOTIFY", "task_id", payload.TaskID)
	case "INSERT", "UPDATE":
		if err := r.AddOrUpdate(ctx, payload.TaskID); err != nil {
			slog.Warn("scheduler: add-or-update failed",
				"task_id", payload.TaskID,
				"op", payload.Op,
				"error", err)
		}
	default:
		slog.Debug("scheduler: unknown NOTIFY op",
			"task_id", payload.TaskID,
			"op", payload.Op)
	}
}
