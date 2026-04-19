package scheduler

import (
	"encoding/json"
	"fmt"
)

// JobExecutePayload is the wire format published to
// matrix.scheduler.job.execute. Python subscribers (queue-group
// "scheduler-exec") deserialize, run the agent turn, write the
// task_executions row via asyncpg, and deliver the result.
//
// Keep this struct in sync with
// python-backend/agent/scheduler/subscriber.py (field names carry
// cross-language).
type JobExecutePayload struct {
	TaskID         string          `json:"task_id"`
	ExecutionID    string          `json:"execution_id"`
	OwnerUserID    string          `json:"owner_user_id"`
	Kind           string          `json:"kind"` // matches scheduled_tasks.kind
	Prompt         string          `json:"prompt,omitempty"`
	SkillIDs       []string        `json:"skill_ids,omitempty"`
	DeliveryTarget json.RawMessage `json:"delivery_target,omitempty"`
	Metadata       json.RawMessage `json:"metadata,omitempty"`
	TraceID        string          `json:"trace_id,omitempty"`
	// FiredAtMs is the scheduler fire time (epoch-ms, UTC). Python uses
	// this to compute end-to-end latency via completed_at - fired_at.
	FiredAtMs int64 `json:"fired_at_ms"`
}

// Validate runs the minimal sanity checks a worker performs before
// publishing. Kept here so handlers in other files can share.
func (p *JobExecutePayload) Validate() error {
	if p.TaskID == "" {
		return fmt.Errorf("task_id required")
	}
	if p.ExecutionID == "" {
		return fmt.Errorf("execution_id required")
	}
	if p.OwnerUserID == "" {
		return fmt.Errorf("owner_user_id required")
	}
	return nil
}

// HeartbeatPayload is published to matrix.scheduler.heartbeat by the
// health_ping infra handler. Consumers (ops dashboards / alerting) read
// this to confirm the scheduler is alive.
type HeartbeatPayload struct {
	TaskID       string `json:"task_id"`
	ExecutionID  string `json:"execution_id"`
	FiredAtMs    int64  `json:"fired_at_ms"`
	SchedulerPID int    `json:"scheduler_pid,omitempty"`
}
