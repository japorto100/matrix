package scheduler

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// Routes returns a minimal http.Handler registry. The caller is expected
// to wire each handler into its own mux (Control-UI BFF proxies to these).
// Authentication is NOT enforced here — handler.Server's hsTokenMiddleware
// handles HS-token auth for all Appservice routes.
//
// Exposed routes (mount under /api/v1/scheduler):
//
//	GET    /tasks           → ListUserTasks (query: user_id, limit)
//	GET    /tasks/{id}      → GetTask
//	PATCH  /tasks/{id}      → PatchTask (body: {"status":"paused|active|cancelled"})
//	DELETE /tasks/{id}      → DeleteTask
//
// POST is intentionally omitted — task creation goes through the agent
// tools in python-backend (chat-first UX rule).
func (s *Scheduler) Routes() map[string]http.HandlerFunc {
	return map[string]http.HandlerFunc{
		"GET /api/v1/scheduler/tasks":        s.handleListTasks,
		"GET /api/v1/scheduler/tasks/{id}":   s.handleGetTask,
		"PATCH /api/v1/scheduler/tasks/{id}": s.handlePatchTask,
		"DELETE /api/v1/scheduler/tasks/{id}": s.handleDeleteTask,
	}
}

type patchBody struct {
	Status string `json:"status"`
}

type taskDTO struct {
	TaskID         string          `json:"task_id"`
	UserID         string          `json:"user_id"`
	Source         string          `json:"source"`
	Kind           string          `json:"kind"`
	CronExpr       string          `json:"cron_expr,omitempty"`
	ScheduledAtMs  int64           `json:"scheduled_at_ms,omitempty"`
	TZ             string          `json:"tz"`
	Prompt         string          `json:"prompt,omitempty"`
	SkillIDs       []string        `json:"skill_ids,omitempty"`
	DeliveryTarget json.RawMessage `json:"delivery_target,omitempty"`
	Status         string          `json:"status"`
	MaxExecutions  int             `json:"max_executions,omitempty"`
	ExecutionCount int             `json:"execution_count"`
	NextRunAtMs    int64           `json:"next_run_at_ms,omitempty"`
	LastRunAtMs    int64           `json:"last_run_at_ms,omitempty"`
	Metadata       json.RawMessage `json:"metadata,omitempty"`
	CreatedAtMs    int64           `json:"created_at_ms"`
	UpdatedAtMs    int64           `json:"updated_at_ms,omitempty"`
}

func toDTO(t *ScheduledTask) taskDTO {
	return taskDTO{
		TaskID:         t.TaskID,
		UserID:         t.UserID,
		Source:         t.Source,
		Kind:           t.Kind,
		CronExpr:       t.CronExpr,
		ScheduledAtMs:  t.ScheduledAtMs,
		TZ:             t.TZ,
		Prompt:         t.Prompt,
		SkillIDs:       t.SkillIDs,
		DeliveryTarget: t.DeliveryTarget,
		Status:         t.Status,
		MaxExecutions:  t.MaxExecutions,
		ExecutionCount: t.ExecutionCount,
		NextRunAtMs:    t.NextRunAtMs,
		LastRunAtMs:    t.LastRunAtMs,
		Metadata:       t.Metadata,
		CreatedAtMs:    t.CreatedAtMs,
		UpdatedAtMs:    t.UpdatedAtMs,
	}
}

func (s *Scheduler) handleListTasks(w http.ResponseWriter, r *http.Request) {
	userID := strings.TrimSpace(r.URL.Query().Get("user_id"))
	if userID == "" {
		writeJSONErr(w, http.StatusBadRequest, "user_id query parameter required")
		return
	}
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	tasks, err := s.store.ListTasksForUser(r.Context(), userID, limit)
	if err != nil {
		// #nosec G706 -- slog structured output escapes user_id; no shell.
		slog.Error("scheduler: list failed", "user_id", userID, "error", err)
		writeJSONErr(w, http.StatusInternalServerError, "list failed")
		return
	}
	out := make([]taskDTO, 0, len(tasks))
	for _, t := range tasks {
		out = append(out, toDTO(t))
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"tasks": out,
		"count": len(out),
	})
}

func (s *Scheduler) handleGetTask(w http.ResponseWriter, r *http.Request) {
	taskID := r.PathValue("id")
	task, err := s.store.LoadTask(r.Context(), taskID)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, toDTO(task))
}

func (s *Scheduler) handlePatchTask(w http.ResponseWriter, r *http.Request) {
	taskID := r.PathValue("id")
	var body patchBody
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSONErr(w, http.StatusBadRequest, "invalid json body")
		return
	}
	nowMs := time.Now().UTC().UnixMilli()
	if err := s.store.PatchStatus(r.Context(), taskID, body.Status, nowMs); err != nil {
		writeStoreErr(w, err)
		return
	}
	// NOTE: the pg_notify trigger fires automatically on UPDATE, so the
	// cron registry hot-reloads without explicit call here.
	writeJSON(w, http.StatusOK, map[string]string{
		"task_id": taskID,
		"status":  body.Status,
	})
}

func (s *Scheduler) handleDeleteTask(w http.ResponseWriter, r *http.Request) {
	taskID := r.PathValue("id")
	if err := s.store.DeleteTask(r.Context(), taskID); err != nil {
		writeStoreErr(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func writeStoreErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, ErrTaskNotFound):
		writeJSONErr(w, http.StatusNotFound, "task not found")
	case errors.Is(err, ErrValidation):
		writeJSONErr(w, http.StatusBadRequest, err.Error())
	default:
		slog.Error("scheduler: store error", "error", err)
		writeJSONErr(w, http.StatusInternalServerError, "internal error")
	}
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeJSONErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
