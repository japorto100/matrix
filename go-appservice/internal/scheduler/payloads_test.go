package scheduler

import (
	"encoding/json"
	"strings"
	"testing"
)

// TestJobExecutePayloadJSONShape guards the cross-language wire format.
// The Python subscriber (agent/scheduler/subscriber.py) expects the exact
// JSON keys produced here. Breaking this contract silently is a bug we
// catch at PR review.
func TestJobExecutePayloadJSONShape(t *testing.T) {
	p := JobExecutePayload{
		TaskID:      "t-1",
		ExecutionID: "e-1",
		OwnerUserID: "user-42",
		Kind:        "recurring",
		Prompt:      "hello",
		SkillIDs:    []string{"skill-a", "skill-b"},
		TraceID:     "trace-xyz",
		FiredAtMs:   1700000000000,
	}
	body, err := json.Marshal(p)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	s := string(body)
	for _, want := range []string{
		`"task_id":"t-1"`,
		`"execution_id":"e-1"`,
		`"owner_user_id":"user-42"`,
		`"kind":"recurring"`,
		`"prompt":"hello"`,
		`"skill_ids":["skill-a","skill-b"]`,
		`"trace_id":"trace-xyz"`,
		`"fired_at_ms":1700000000000`,
	} {
		if !strings.Contains(s, want) {
			t.Errorf("marshaled payload missing key: %s\nfull: %s", want, s)
		}
	}
}

func TestJobExecutePayloadValidateRequiresFields(t *testing.T) {
	cases := []struct {
		name    string
		payload JobExecutePayload
		wantErr string
	}{
		{
			name:    "missing task_id",
			payload: JobExecutePayload{ExecutionID: "e", OwnerUserID: "u"},
			wantErr: "task_id",
		},
		{
			name:    "missing execution_id",
			payload: JobExecutePayload{TaskID: "t", OwnerUserID: "u"},
			wantErr: "execution_id",
		},
		{
			name:    "missing owner_user_id",
			payload: JobExecutePayload{TaskID: "t", ExecutionID: "e"},
			wantErr: "owner_user_id",
		},
		{
			name:    "ok",
			payload: JobExecutePayload{TaskID: "t", ExecutionID: "e", OwnerUserID: "u"},
			wantErr: "",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			err := c.payload.Validate()
			if c.wantErr == "" {
				if err != nil {
					t.Fatalf("unexpected err: %v", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), c.wantErr) {
				t.Fatalf("want err contains %q, got %v", c.wantErr, err)
			}
		})
	}
}

func TestSchedulerConstantsAreStable(t *testing.T) {
	// These must stay in lockstep with python-backend/agent/scheduler/__init__.py.
	if DefaultServiceUserID != "scheduler-service" {
		t.Errorf("DefaultServiceUserID changed")
	}
	if DefaultJetStreamStream != "SCHEDULER" {
		t.Errorf("DefaultJetStreamStream changed")
	}
	if DefaultQueueGroup != "scheduler-exec" {
		t.Errorf("DefaultQueueGroup changed")
	}
	if SubjectJobExecute != "matrix.scheduler.job.execute" {
		t.Errorf("SubjectJobExecute changed")
	}
	if SubjectHeartbeat != "matrix.scheduler.heartbeat" {
		t.Errorf("SubjectHeartbeat changed")
	}
	if Schema != "scheduler" {
		t.Errorf("Schema changed")
	}
}
