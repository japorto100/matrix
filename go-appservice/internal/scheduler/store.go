package scheduler

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ScheduledTask mirrors a row from scheduler.scheduled_tasks with only the
// fields the dispatch path and REST routes need.
type ScheduledTask struct {
	TaskID         string
	UserID         string
	Source         string
	Kind           string
	CronExpr       string
	ScheduledAtMs  int64
	TZ             string
	Prompt         string
	SkillIDs       []string
	DeliveryTarget json.RawMessage
	Status         string
	MaxExecutions  int
	ExecutionCount int
	NextRunAtMs    int64
	LastRunAtMs    int64
	Metadata       json.RawMessage
	CreatedAtMs    int64
	UpdatedAtMs    int64
}

// TaskLoader reads a single task row. Small interface so the matrix
// dispatch worker can be unit-tested without a real DB.
type TaskLoader interface {
	LoadTask(ctx context.Context, taskID string) (*ScheduledTask, error)
}

// ExecutionStore writes task_executions rows.
type ExecutionStore interface {
	BeginExecution(ctx context.Context, taskID string, firedAt time.Time) (executionID string, err error)
}

// PgStore implements both TaskLoader and ExecutionStore against the
// shared pgxpool.
type PgStore struct {
	Pool *pgxpool.Pool
}

// LoadTask fetches one scheduled_tasks row. Returns ErrTaskNotFound when
// the row is missing (e.g. deleted between fire-schedule and work).
func (s *PgStore) LoadTask(ctx context.Context, taskID string) (*ScheduledTask, error) {
	const sql = `SELECT task_id, user_id, source, kind,
	                     COALESCE(cron_expr, ''),
	                     COALESCE(scheduled_at, 0),
	                     tz,
	                     COALESCE(prompt, ''),
	                     COALESCE(skill_ids, ARRAY[]::TEXT[]),
	                     delivery_target,
	                     status,
	                     COALESCE(max_executions, 0),
	                     execution_count,
	                     COALESCE(next_run_at, 0),
	                     COALESCE(last_run_at, 0),
	                     metadata,
	                     created_at,
	                     COALESCE(updated_at, 0)
	              FROM scheduler.scheduled_tasks
	              WHERE task_id = $1`
	row := s.Pool.QueryRow(ctx, sql, taskID)
	var t ScheduledTask
	var deliveryTarget, metadata []byte
	if err := row.Scan(
		&t.TaskID,
		&t.UserID,
		&t.Source,
		&t.Kind,
		&t.CronExpr,
		&t.ScheduledAtMs,
		&t.TZ,
		&t.Prompt,
		&t.SkillIDs,
		&deliveryTarget,
		&t.Status,
		&t.MaxExecutions,
		&t.ExecutionCount,
		&t.NextRunAtMs,
		&t.LastRunAtMs,
		&metadata,
		&t.CreatedAtMs,
		&t.UpdatedAtMs,
	); err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrTaskNotFound
		}
		return nil, fmt.Errorf("scan scheduled_task: %w", err)
	}
	if len(deliveryTarget) > 0 {
		t.DeliveryTarget = json.RawMessage(deliveryTarget)
	}
	if len(metadata) > 0 {
		t.Metadata = json.RawMessage(metadata)
	}
	return &t, nil
}

// ListActiveTasks returns all rows with status='active' that have a
// cron_expr (recurring / routine / condition / infra). one_shot / reminder
// rows are dispatched via River's ScheduledAt insert in Phase 2.
func (s *PgStore) ListActiveTasks(ctx context.Context) ([]*ScheduledTask, error) {
	const sql = `SELECT task_id, user_id, source, kind,
	                     COALESCE(cron_expr, ''),
	                     COALESCE(scheduled_at, 0),
	                     tz,
	                     COALESCE(prompt, ''),
	                     COALESCE(skill_ids, ARRAY[]::TEXT[]),
	                     delivery_target,
	                     status,
	                     COALESCE(max_executions, 0),
	                     execution_count,
	                     COALESCE(next_run_at, 0),
	                     COALESCE(last_run_at, 0),
	                     metadata,
	                     created_at,
	                     COALESCE(updated_at, 0)
	              FROM scheduler.scheduled_tasks
	              WHERE status = 'active' AND cron_expr IS NOT NULL`
	rows, err := s.Pool.Query(ctx, sql)
	if err != nil {
		return nil, fmt.Errorf("list active tasks: %w", err)
	}
	defer rows.Close()
	var out []*ScheduledTask
	for rows.Next() {
		var t ScheduledTask
		var deliveryTarget, metadata []byte
		if err := rows.Scan(
			&t.TaskID,
			&t.UserID,
			&t.Source,
			&t.Kind,
			&t.CronExpr,
			&t.ScheduledAtMs,
			&t.TZ,
			&t.Prompt,
			&t.SkillIDs,
			&deliveryTarget,
			&t.Status,
			&t.MaxExecutions,
			&t.ExecutionCount,
			&t.NextRunAtMs,
			&t.LastRunAtMs,
			&metadata,
			&t.CreatedAtMs,
			&t.UpdatedAtMs,
		); err != nil {
			return nil, fmt.Errorf("scan row: %w", err)
		}
		if len(deliveryTarget) > 0 {
			t.DeliveryTarget = json.RawMessage(deliveryTarget)
		}
		if len(metadata) > 0 {
			t.Metadata = json.RawMessage(metadata)
		}
		out = append(out, &t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate active tasks: %w", err)
	}
	return out, nil
}

// BeginExecution inserts a row in task_executions with status='running'
// and returns the generated execution_id. Called by the MatrixDispatchWorker
// at fire-time; the Python subscriber updates the row to 'completed' /
// 'failed' when the agent turn finishes.
func (s *PgStore) BeginExecution(ctx context.Context, taskID string, firedAt time.Time) (string, error) {
	executionID, err := newULID()
	if err != nil {
		return "", err
	}
	_, err = s.Pool.Exec(ctx, `
		INSERT INTO scheduler.task_executions
			(execution_id, task_id, started_at, status)
		VALUES ($1, $2, $3, 'running')
	`, executionID, taskID, firedAt.UnixMilli())
	if err != nil {
		return "", fmt.Errorf("insert task_execution: %w", err)
	}
	// Update the parent row's last_run_at + execution_count so the UI can
	// reflect activity without joining task_executions.
	_, err = s.Pool.Exec(ctx, `
		UPDATE scheduler.scheduled_tasks
		SET last_run_at = $1,
		    execution_count = execution_count + 1,
		    updated_at = $1
		WHERE task_id = $2
	`, firedAt.UnixMilli(), taskID)
	if err != nil {
		return "", fmt.Errorf("update task timestamps: %w", err)
	}
	return executionID, nil
}

// TaskExecution mirrors a scheduler.task_executions row for the Control-UI
// runs-drawer. Kept near the DB layer so REST handlers can project into
// the wire DTO trivially.
type TaskExecution struct {
	ExecutionID    string
	TaskID         string
	StartedAtMs    int64
	CompletedAtMs  int64
	Status         string
	ResultSummary  string
	Error          string
	TraceID        string
	DurationMs     int
}

// ListExecutions returns up to `limit` recent executions of taskID
// (most recent first). Ownership check lives in the REST handler — this
// layer assumes the caller already confirmed taskID belongs to user.
func (s *PgStore) ListExecutions(ctx context.Context, taskID string, limit int) ([]*TaskExecution, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	rows, err := s.Pool.Query(ctx, `
		SELECT execution_id,
		       task_id,
		       started_at,
		       COALESCE(completed_at, 0),
		       status,
		       COALESCE(result_summary, ''),
		       COALESCE(error, ''),
		       COALESCE(trace_id, ''),
		       COALESCE(duration_ms, 0)
		FROM scheduler.task_executions
		WHERE task_id = $1
		ORDER BY started_at DESC
		LIMIT $2`, taskID, limit)
	if err != nil {
		return nil, fmt.Errorf("list executions: %w", err)
	}
	defer rows.Close()
	var out []*TaskExecution
	for rows.Next() {
		var t TaskExecution
		if err := rows.Scan(
			&t.ExecutionID,
			&t.TaskID,
			&t.StartedAtMs,
			&t.CompletedAtMs,
			&t.Status,
			&t.ResultSummary,
			&t.Error,
			&t.TraceID,
			&t.DurationMs,
		); err != nil {
			return nil, fmt.Errorf("scan execution row: %w", err)
		}
		out = append(out, &t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate executions: %w", err)
	}
	return out, nil
}

// PatchStatus updates only the status column (used by REST pause/resume/cancel).
// Ownership-gated: the WHERE clause includes user_id so a caller with a
// known task_id cannot touch tasks that belong to a different user.
// Returns ErrTaskNotFound when no row matches (either missing or
// user_id mismatch — same error to avoid task-id enumeration).
func (s *PgStore) PatchStatus(ctx context.Context, taskID, userID, newStatus string, nowMs int64) error {
	allowed := map[string]bool{
		"active":    true,
		"paused":    true,
		"cancelled": true,
	}
	if !allowed[newStatus] {
		return fmt.Errorf("%w: status %q not allowed (active|paused|cancelled)", ErrValidation, newStatus)
	}
	if strings.TrimSpace(userID) == "" {
		return fmt.Errorf("%w: user_id required", ErrValidation)
	}
	tag, err := s.Pool.Exec(ctx, `
		UPDATE scheduler.scheduled_tasks
		SET status = $1, updated_at = $2
		WHERE task_id = $3 AND user_id = $4
	`, newStatus, nowMs, taskID, userID)
	if err != nil {
		return fmt.Errorf("patch status: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrTaskNotFound
	}
	return nil
}

// DeleteTask removes a task row (cascades to task_executions). Ownership-gated.
func (s *PgStore) DeleteTask(ctx context.Context, taskID, userID string) error {
	if strings.TrimSpace(userID) == "" {
		return fmt.Errorf("%w: user_id required", ErrValidation)
	}
	tag, err := s.Pool.Exec(ctx,
		`DELETE FROM scheduler.scheduled_tasks WHERE task_id = $1 AND user_id = $2`,
		taskID, userID)
	if err != nil {
		return fmt.Errorf("delete task: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrTaskNotFound
	}
	return nil
}

// ListTasksForUser returns all rows owned by userID (any status). Used by
// the Control-UI list page.
func (s *PgStore) ListTasksForUser(ctx context.Context, userID string, limit int) ([]*ScheduledTask, error) {
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return nil, fmt.Errorf("%w: user_id required", ErrValidation)
	}
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	rows, err := s.Pool.Query(ctx, `
		SELECT task_id, user_id, source, kind,
		       COALESCE(cron_expr, ''),
		       COALESCE(scheduled_at, 0),
		       tz,
		       COALESCE(prompt, ''),
		       COALESCE(skill_ids, ARRAY[]::TEXT[]),
		       delivery_target,
		       status,
		       COALESCE(max_executions, 0),
		       execution_count,
		       COALESCE(next_run_at, 0),
		       COALESCE(last_run_at, 0),
		       metadata,
		       created_at,
		       COALESCE(updated_at, 0)
		FROM scheduler.scheduled_tasks
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT $2`, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("list tasks for user: %w", err)
	}
	defer rows.Close()
	var out []*ScheduledTask
	for rows.Next() {
		var t ScheduledTask
		var deliveryTarget, metadata []byte
		if err := rows.Scan(
			&t.TaskID,
			&t.UserID,
			&t.Source,
			&t.Kind,
			&t.CronExpr,
			&t.ScheduledAtMs,
			&t.TZ,
			&t.Prompt,
			&t.SkillIDs,
			&deliveryTarget,
			&t.Status,
			&t.MaxExecutions,
			&t.ExecutionCount,
			&t.NextRunAtMs,
			&t.LastRunAtMs,
			&metadata,
			&t.CreatedAtMs,
			&t.UpdatedAtMs,
		); err != nil {
			return nil, fmt.Errorf("scan user task: %w", err)
		}
		if len(deliveryTarget) > 0 {
			t.DeliveryTarget = json.RawMessage(deliveryTarget)
		}
		if len(metadata) > 0 {
			t.Metadata = json.RawMessage(metadata)
		}
		out = append(out, &t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate user tasks: %w", err)
	}
	return out, nil
}

// Sentinel errors surfaced to the HTTP layer.
var (
	ErrTaskNotFound = errors.New("scheduled task not found")
	ErrValidation   = errors.New("validation failed")
)

func newULID() (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("random: %w", err)
	}
	return hex.EncodeToString(buf), nil
}
