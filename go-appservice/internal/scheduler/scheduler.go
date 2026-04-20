// Package scheduler runs recurring / one-shot tasks against the shared
// pgxpool using River (Postgres-native job queue, MPL-2.0).
//
// Layering:
//
//	Alembic owns schema `scheduler` (Migration 019): scheduled_tasks,
//	task_executions. River owns its own tables in the same schema via
//	rivermigrate (river_job, river_leader, river_migration).
//
// Dispatch flow:
//
//	cron_registry   —→   River periodic job   —→   matrix_dispatch handler
//	                                              —→ NATS JetStream publish
//	                                                  matrix.scheduler.job.execute
//	                                              —→ Python subscriber runs
//	                                                  agent turn, writes
//	                                                  task_executions row,
//	                                                  delivers via Matrix
//	                                                  bridge.
//
// exec-scheduler Phase-1 Lane B. Fully wired via handler.Server.
package scheduler

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
	"github.com/riverqueue/river/riverdriver/riverpgxv5"
	"github.com/riverqueue/river/rivermigrate"
)

// Well-known identifiers + NATS subjects used across Go + Python.
// Keep in sync with python-backend/agent/scheduler/__init__.py.
const (
	// DefaultServiceUserID is the pseudo-user that owns infrastructure
	// tasks (health-ping, memory-prune, metric-rollup, etc.). Overridable
	// via SCHEDULER_SERVICE_USER_ID env-var.
	DefaultServiceUserID = "scheduler-service"

	// DefaultJetStreamStream is the JetStream stream name for
	// matrix.scheduler.> subjects. Overridable via
	// SCHEDULER_JETSTREAM_STREAM.
	DefaultJetStreamStream = "SCHEDULER"

	// DefaultQueueGroup is the NATS JetStream durable-consumer name for
	// Python subscribers. Identical names deliver queue-group semantics
	// (exactly-once across workers).
	DefaultQueueGroup = "scheduler-exec"

	// Schema is the Postgres schema that owns scheduler tables AND where
	// River creates its own river_* tables (via river.Config.Schema).
	Schema = "scheduler"

	// SubjectJobExecute is the NATS subject for agent-turn dispatch.
	// Payload: JobExecutePayload.
	SubjectJobExecute = "matrix.scheduler.job.execute"

	// SubjectHeartbeat is used by the health-ping infra handler.
	SubjectHeartbeat = "matrix.scheduler.heartbeat"

	// QueueScheduler is the River queue name Phase-1 workers live on.
	// One queue keeps job ordering predictable for debugging.
	QueueScheduler = "scheduler"
)

// ServiceUserID returns the configured infra-task user id, falling back to
// DefaultServiceUserID if SCHEDULER_SERVICE_USER_ID is unset.
func ServiceUserID() string {
	if v := os.Getenv("SCHEDULER_SERVICE_USER_ID"); v != "" {
		return v
	}
	return DefaultServiceUserID
}

// Config captures runtime knobs. Sensible defaults are applied in New.
type Config struct {
	// MaxWorkers is the per-queue concurrency cap. Phase-1 default 8 —
	// infra-handlers are cheap, matrix-dispatch publishes and returns
	// immediately (actual turn work is Python-side).
	MaxWorkers int

	// HealthPingSchedule is the cron expression for the infra health-ping.
	// Default: every minute.
	HealthPingSchedule string

	// MemoryPruneSchedule is the cron expression for memory-prune. Default:
	// weekly Monday 03:00 UTC.
	MemoryPruneSchedule string

	// MetricRollupSchedule is the cron expression for hourly
	// aggregation into agent.metrics. Default: every hour at :05.
	MetricRollupSchedule string

	// HarnessBackfillSchedule is the cron expression for the Phase-C
	// A/B-experiment scorer backfill (exec-scheduler §8.1). Calls Python
	// /internal/harness/backfill. Default: every 15 minutes.
	HarnessBackfillSchedule string
}

// Scheduler is the process-level scheduler entrypoint.
type Scheduler struct {
	pool        *pgxpool.Pool
	store       *PgStore
	client      *river.Client[pgx.Tx]
	cronReg     *CronRegistry
	watchCancel context.CancelFunc
	watchDone   chan struct{}
	cfg            Config
	jsProvider     JetStreamProvider
	pruneClient    MemoryPruneClient
	harnessClient  HarnessBackfillClient
}

// JetStreamProvider abstracts the path that produces the JetStream
// context at Start() time. handler.Server provides this by calling
// natsbridge.Bridge.JetStreamPublisher() once the connection is up.
type JetStreamProvider interface {
	JetStream() (jsContext, error)
	EnsureStream(ctx context.Context, stream, subjectPrefix string) error
}

// New constructs a Scheduler. client is nil until Start() runs.
func New(
	pool *pgxpool.Pool,
	cfg Config,
	js JetStreamProvider,
	prune MemoryPruneClient,
	harness HarnessBackfillClient,
) (*Scheduler, error) {
	if pool == nil {
		return nil, fmt.Errorf("pool required")
	}
	if js == nil {
		return nil, fmt.Errorf("jetstream provider required")
	}
	if cfg.MaxWorkers <= 0 {
		cfg.MaxWorkers = 8
	}
	if cfg.HealthPingSchedule == "" {
		cfg.HealthPingSchedule = "* * * * *" // every minute
	}
	if cfg.MemoryPruneSchedule == "" {
		cfg.MemoryPruneSchedule = "0 3 * * 1" // Mon 03:00 UTC
	}
	if cfg.MetricRollupSchedule == "" {
		cfg.MetricRollupSchedule = "5 * * * *" // every hour at :05
	}
	if cfg.HarnessBackfillSchedule == "" {
		cfg.HarnessBackfillSchedule = "*/15 * * * *" // every 15 minutes
	}
	return &Scheduler{
		pool:          pool,
		store:         &PgStore{Pool: pool},
		cfg:           cfg,
		jsProvider:    js,
		pruneClient:   prune,
		harnessClient: harness,
	}, nil
}

// Start boots the scheduler:
//  1. Ensure JetStream stream exists
//  2. Run rivermigrate Up (idempotent)
//  3. Build workers + periodic-job seeds for infra handlers
//  4. Construct River client with our schema
//  5. Client.Start (workers begin fetching)
//  6. Load active scheduled_tasks into CronRegistry
//  7. Launch WatchNotifications in a goroutine
func (s *Scheduler) Start(ctx context.Context) error {
	// 1. JetStream stream setup
	if err := s.jsProvider.EnsureStream(ctx, DefaultJetStreamStream, "matrix.scheduler."); err != nil {
		return fmt.Errorf("ensure jetstream: %w", err)
	}
	js, err := s.jsProvider.JetStream()
	if err != nil {
		return fmt.Errorf("get jetstream: %w", err)
	}

	// 2. Run rivermigrate Up.
	driver := riverpgxv5.New(s.pool)
	migrator, err := rivermigrate.New(driver, &rivermigrate.Config{
		Schema: Schema,
	})
	if err != nil {
		return fmt.Errorf("rivermigrate new: %w", err)
	}
	if _, migErr := migrator.Migrate(ctx, rivermigrate.DirectionUp, nil); migErr != nil {
		return fmt.Errorf("rivermigrate up: %w", migErr)
	}
	slog.Info("scheduler: river tables migrated", "schema", Schema)

	// 3. Workers + infra PeriodicJob seeds.
	workers := river.NewWorkers()
	river.AddWorker(workers, &MatrixDispatchWorker{
		JS:        js,
		Loader:    s.store,
		ExecStore: s.store,
	})
	river.AddWorker(workers, &HealthPingWorker{JS: js})
	river.AddWorker(workers, &MemoryPruneWorker{PruneClient: s.pruneClient})
	river.AddWorker(workers, &MetricRollupWorker{Pool: s.pool})
	river.AddWorker(workers, &HarnessBackfillWorker{Client: s.harnessClient})

	// Infra periodic jobs — seeded in Config so River runs them even if
	// scheduled_tasks has no rows yet. They are NOT represented in
	// scheduled_tasks (owner_kind=system lives in code, not DB).
	healthSched, err := parseStandardSchedule(s.cfg.HealthPingSchedule)
	if err != nil {
		return fmt.Errorf("parse health_ping schedule: %w", err)
	}
	pruneSched, err := parseStandardSchedule(s.cfg.MemoryPruneSchedule)
	if err != nil {
		return fmt.Errorf("parse memory_prune schedule: %w", err)
	}
	rollupSched, err := parseStandardSchedule(s.cfg.MetricRollupSchedule)
	if err != nil {
		return fmt.Errorf("parse metric_rollup schedule: %w", err)
	}
	harnessSched, err := parseStandardSchedule(s.cfg.HarnessBackfillSchedule)
	if err != nil {
		return fmt.Errorf("parse harness_backfill schedule: %w", err)
	}
	periodics := []*river.PeriodicJob{
		river.NewPeriodicJob(
			healthSched,
			func() (river.JobArgs, *river.InsertOpts) { return HealthPingArgs{}, nil },
			&river.PeriodicJobOpts{},
		),
		river.NewPeriodicJob(
			pruneSched,
			func() (river.JobArgs, *river.InsertOpts) { return MemoryPruneArgs{}, nil },
			&river.PeriodicJobOpts{},
		),
		river.NewPeriodicJob(
			rollupSched,
			func() (river.JobArgs, *river.InsertOpts) { return MetricRollupArgs{}, nil },
			&river.PeriodicJobOpts{},
		),
		river.NewPeriodicJob(
			harnessSched,
			func() (river.JobArgs, *river.InsertOpts) { return HarnessBackfillArgs{}, nil },
			&river.PeriodicJobOpts{},
		),
	}

	// 4. Construct client.
	client, err := river.NewClient(driver, &river.Config{
		Schema: Schema,
		Queues: map[string]river.QueueConfig{
			QueueScheduler: {MaxWorkers: s.cfg.MaxWorkers},
		},
		Workers:      workers,
		PeriodicJobs: periodics,
		JobTimeout:   2 * time.Minute,
	})
	if err != nil {
		return fmt.Errorf("river newclient: %w", err)
	}
	s.client = client

	// 5. Start the client.
	if err := client.Start(ctx); err != nil {
		return fmt.Errorf("river start: %w", err)
	}

	// 6. Cron registry for user/admin tasks.
	s.cronReg = NewCronRegistry(client, s.store)
	if err := s.cronReg.Reload(ctx); err != nil {
		return fmt.Errorf("cron registry reload: %w", err)
	}

	// 7. NOTIFY watcher goroutine — cancellable from Stop().
	watchCtx, cancel := context.WithCancel(context.Background())
	s.watchCancel = cancel
	s.watchDone = make(chan struct{})
	go func() {
		defer close(s.watchDone)
		if err := s.cronReg.WatchNotifications(watchCtx, s.pool); err != nil && watchCtx.Err() == nil {
			slog.Error("scheduler: notification watcher stopped", "error", err)
		}
	}()

	slog.Info("scheduler: started",
		"schema", Schema,
		"queue", QueueScheduler,
		"max_workers", s.cfg.MaxWorkers)
	return nil
}

// Stop shuts the scheduler down. Called from handler.Server.Stop()
// BEFORE httpServer.Shutdown so in-flight River jobs finish publishing
// their NATS messages before the HTTP layer is torn down. The NATS
// connection itself is drained by main.go's defer natsBridge.Close()
// AFTER this call, so our final publishes land safely.
//
// Shutdown budget: 30s for River drain. If jobs don't finish in that
// window River escalates via its own timeout.
func (s *Scheduler) Stop(ctx context.Context) error {
	// Cancel the NOTIFY watcher first so it stops trying to touch the pool.
	if s.watchCancel != nil {
		s.watchCancel()
	}
	if s.watchDone != nil {
		<-s.watchDone
	}
	if s.client == nil {
		return nil
	}
	stopCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	if err := s.client.Stop(stopCtx); err != nil {
		return fmt.Errorf("river stop: %w", err)
	}
	return nil
}

// Store exposes the backing PgStore so REST handlers can query directly.
func (s *Scheduler) Store() *PgStore { return s.store }
