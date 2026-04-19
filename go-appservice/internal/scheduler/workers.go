package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nats-io/nats.go"
	"github.com/riverqueue/river"
)

// ── River Job-Args ───────────────────────────────────────────────────────

// MatrixDispatchArgs is the River job args type for user/admin scheduled
// tasks that require an agent turn. The worker publishes a
// matrix.scheduler.job.execute NATS JetStream message and returns;
// Python-side subscriber picks it up, runs the turn, delivers the result.
//
// TaskID references scheduler.scheduled_tasks.task_id. The worker reads
// the row at fire-time (not insertion-time) so pause/edit between
// insertion and fire take effect.
type MatrixDispatchArgs struct {
	TaskID string `json:"task_id"`
}

// Kind returns the job kind name stored in river_job.kind.
func (MatrixDispatchArgs) Kind() string { return "scheduler.matrix_dispatch" }

// HealthPingArgs triggers the health-ping infra handler.
type HealthPingArgs struct{}

// Kind returns the job kind name.
func (HealthPingArgs) Kind() string { return "scheduler.health_ping" }

// MemoryPruneArgs triggers the memory-prune infra handler (calls Python
// /internal/memory/prune).
type MemoryPruneArgs struct{}

// Kind returns the job kind name.
func (MemoryPruneArgs) Kind() string { return "scheduler.memory_prune" }

// MetricRollupArgs triggers the hourly aggregation into agent.metrics.
// Reads counts from agent.traces / agent.spans / scheduler.task_executions
// for the just-closed hour and inserts one row per metric into agent.metrics.
type MetricRollupArgs struct{}

// Kind returns the job kind name.
func (MetricRollupArgs) Kind() string { return "scheduler.metric_rollup" }

// ── River Workers ────────────────────────────────────────────────────────

// jsContext is the minimal NATS JetStream surface the workers need. Kept
// as an interface so tests can substitute a fake.
type jsContext interface {
	Publish(subj string, data []byte, opts ...nats.PubOpt) (*nats.PubAck, error)
}

// MatrixDispatchWorker fires a NATS JetStream message per scheduled task.
// Persistence-guarantee: JetStream acks the publish only after the message
// is durably stored, so a Python subscriber crash/replay window doesn't
// lose the fire.
type MatrixDispatchWorker struct {
	river.WorkerDefaults[MatrixDispatchArgs]

	JS        jsContext
	Loader    TaskLoader
	ExecStore ExecutionStore
	Now       func() time.Time // injectable for tests
}

// Work implements river.Worker.
func (w *MatrixDispatchWorker) Work(ctx context.Context, job *river.Job[MatrixDispatchArgs]) error {
	now := w.now()
	task, err := w.Loader.LoadTask(ctx, job.Args.TaskID)
	if err != nil {
		return fmt.Errorf("load task %s: %w", job.Args.TaskID, err)
	}
	if task.Status != "active" {
		// Task was paused/cancelled between fire scheduling and execution —
		// skip silently (River marks job done, no retry).
		slog.Debug("scheduler: skipping non-active task",
			"task_id", task.TaskID, "status", task.Status)
		return nil
	}

	executionID, err := w.ExecStore.BeginExecution(ctx, task.TaskID, now)
	if err != nil {
		return fmt.Errorf("begin execution for %s: %w", task.TaskID, err)
	}

	payload := JobExecutePayload{
		TaskID:         task.TaskID,
		ExecutionID:    executionID,
		OwnerUserID:    task.UserID,
		Kind:           task.Kind,
		Prompt:         task.Prompt,
		SkillIDs:       task.SkillIDs,
		DeliveryTarget: task.DeliveryTarget,
		Metadata:       task.Metadata,
		FiredAtMs:      now.UnixMilli(),
	}
	if validErr := payload.Validate(); validErr != nil {
		return fmt.Errorf("build payload: %w", validErr)
	}

	body, marshalErr := json.Marshal(payload)
	if marshalErr != nil {
		return fmt.Errorf("marshal payload: %w", marshalErr)
	}

	if _, pubErr := w.JS.Publish(SubjectJobExecute, body); pubErr != nil {
		return fmt.Errorf("jetstream publish %s: %w", SubjectJobExecute, pubErr)
	}

	slog.Info("scheduler: task dispatched",
		"task_id", task.TaskID,
		"execution_id", executionID,
		"kind", task.Kind,
		"subject", SubjectJobExecute,
	)
	return nil
}

// HealthPingWorker publishes a heartbeat. Phase-1 proof that the in-process
// dispatch pipeline works without touching Python.
type HealthPingWorker struct {
	river.WorkerDefaults[HealthPingArgs]

	JS  jsContext
	Now func() time.Time
}

// Work implements river.Worker.
func (w *HealthPingWorker) Work(ctx context.Context, job *river.Job[HealthPingArgs]) error {
	now := w.now()
	payload := HeartbeatPayload{
		TaskID:       "infra.health_ping",
		ExecutionID:  fmt.Sprintf("hp-%d", now.UnixNano()),
		FiredAtMs:    now.UnixMilli(),
		SchedulerPID: os.Getpid(),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal heartbeat: %w", err)
	}
	if _, err := w.JS.Publish(SubjectHeartbeat, body); err != nil {
		return fmt.Errorf("publish heartbeat: %w", err)
	}
	slog.Debug("scheduler: heartbeat published",
		"execution_id", payload.ExecutionID)
	return nil
}

// MemoryPruneWorker calls the Python /internal/memory/prune endpoint.
// Phase-1 runs the HTTP call; actual prune logic lives in
// python-backend/agent/scheduler/handlers/memory_prune.py.
type MemoryPruneWorker struct {
	river.WorkerDefaults[MemoryPruneArgs]

	PruneClient MemoryPruneClient
	Now         func() time.Time
}

// Work implements river.Worker.
func (w *MemoryPruneWorker) Work(ctx context.Context, _ *river.Job[MemoryPruneArgs]) error {
	if w.PruneClient == nil {
		slog.Warn("scheduler: memory_prune skipped — no client wired")
		return nil
	}
	if err := w.PruneClient.Prune(ctx); err != nil {
		return fmt.Errorf("memory prune: %w", err)
	}
	slog.Info("scheduler: memory prune completed")
	return nil
}

// MemoryPruneClient is the minimal surface the worker needs from any HTTP
// client (keeps test seams narrow).
type MemoryPruneClient interface {
	Prune(ctx context.Context) error
}

// MetricRollupWorker aggregates counters for the just-closed hour into
// agent.metrics. Reads from scheduler.task_executions (counts by status)
// and from agent.traces (if exec-18 is wired). Idempotent: uses
// (name, bucket_ts) PK with ON CONFLICT DO UPDATE.
type MetricRollupWorker struct {
	river.WorkerDefaults[MetricRollupArgs]

	Pool *pgxpool.Pool
	Now  func() time.Time
}

// Work implements river.Worker.
func (w *MetricRollupWorker) Work(ctx context.Context, _ *river.Job[MetricRollupArgs]) error {
	now := w.now()
	// Bucket = start of the *previous* hour (closed interval).
	bucketEnd := now.Truncate(time.Hour)
	bucketStart := bucketEnd.Add(-time.Hour)
	bucketTsMs := bucketStart.UnixMilli()

	// scheduler.task_executions grouped by status for the bucket window.
	rows, err := w.Pool.Query(ctx, `
		SELECT status, COUNT(*)
		FROM scheduler.task_executions
		WHERE started_at >= $1 AND started_at < $2
		GROUP BY status
	`, bucketStart.UnixMilli(), bucketEnd.UnixMilli())
	if err != nil {
		return fmt.Errorf("count task_executions: %w", err)
	}
	defer rows.Close()

	type counted struct {
		status string
		count  int64
	}
	var seen []counted
	for rows.Next() {
		var c counted
		if scanErr := rows.Scan(&c.status, &c.count); scanErr != nil {
			return fmt.Errorf("scan: %w", scanErr)
		}
		seen = append(seen, c)
	}
	if iterErr := rows.Err(); iterErr != nil {
		return fmt.Errorf("iterate: %w", iterErr)
	}

	// Upsert one metric row per status observed. Zero-counts aren't
	// materialised — consumers treat absence as zero, same convention as
	// Prometheus.
	for _, c := range seen {
		name := "scheduler.task_executions." + c.status
		if _, execErr := w.Pool.Exec(ctx, `
			INSERT INTO agent.metrics
				(name, bucket_ts, kind, value, labels, created_at)
			VALUES ($1, $2, 'counter', $3, NULL, $4)
			ON CONFLICT (name, bucket_ts) DO UPDATE
			SET value = EXCLUDED.value, created_at = EXCLUDED.created_at
		`, name, bucketTsMs, c.count, now.UnixMilli()); execErr != nil {
			return fmt.Errorf("upsert metric %s: %w", name, execErr)
		}
	}
	slog.Info("scheduler: metric rollup completed",
		"bucket_start", bucketStart,
		"rows_upserted", len(seen))
	return nil
}

// Helpers so tests can inject time.

func (w *MatrixDispatchWorker) now() time.Time {
	if w.Now != nil {
		return w.Now().UTC()
	}
	return time.Now().UTC()
}

func (w *HealthPingWorker) now() time.Time {
	if w.Now != nil {
		return w.Now().UTC()
	}
	return time.Now().UTC()
}

func (w *MetricRollupWorker) now() time.Time {
	if w.Now != nil {
		return w.Now().UTC()
	}
	return time.Now().UTC()
}
