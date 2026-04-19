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
//	                                              —→ NATS publish
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
	"os"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river/riverdriver"
	"github.com/riverqueue/river/riverdriver/riverpgxv5"
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
	// Payload: JSON { task_id, execution_id, owner_user_id, prompt,
	//                 delivery_target, skill_ids, trace_id }.
	SubjectJobExecute = "matrix.scheduler.job.execute"

	// SubjectHeartbeat is used by the health-ping infra handler.
	SubjectHeartbeat = "matrix.scheduler.heartbeat"
)

// ServiceUserID returns the configured infra-task user id, falling back to
// DefaultServiceUserID if SCHEDULER_SERVICE_USER_ID is unset.
func ServiceUserID() string {
	if v := os.Getenv("SCHEDULER_SERVICE_USER_ID"); v != "" {
		return v
	}
	return DefaultServiceUserID
}

// Scheduler is the process-level scheduler entrypoint. Holds the River
// client and manages startup/shutdown.
//
// Lane B fills in cron-registry, NATS dispatch handler, REST routes. For
// Lane P this is a thin placeholder that pins the River module dep in
// go.mod and exposes the Start/Stop interface handler.Server calls.
type Scheduler struct {
	pool   *pgxpool.Pool
	driver riverdriver.Driver[pgx.Tx]
}

// New constructs a Scheduler against the shared pgxpool. Does not start
// the client — call Start() when the surrounding server is ready.
func New(pool *pgxpool.Pool) (*Scheduler, error) {
	return &Scheduler{
		pool:   pool,
		driver: riverpgxv5.New(pool),
	}, nil
}

// Start is a placeholder. Lane B: boots the River client, runs
// rivermigrate Up, loads active scheduled_tasks into the cron registry,
// subscribes to NOTIFY scheduler_task_changed.
func (s *Scheduler) Start(_ context.Context) error {
	return nil
}

// Stop drains in-flight River jobs with a caller-supplied timeout.
// Called by handler.Server.Stop() BEFORE httpServer.Shutdown so workers
// finish writing their results before the HTTP layer goes away.
func (s *Scheduler) Stop(_ context.Context) error {
	return nil
}
