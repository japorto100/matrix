package scheduler

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/riverqueue/river"
)

// fakeJetStream captures Publish calls without touching a real broker.
type fakeJetStream struct {
	publishes []publishedMsg
	returnErr error
}

type publishedMsg struct {
	Subject string
	Body    []byte
}

func (f *fakeJetStream) Publish(subj string, data []byte, _ ...nats.PubOpt) (*nats.PubAck, error) {
	if f.returnErr != nil {
		return nil, f.returnErr
	}
	f.publishes = append(f.publishes, publishedMsg{Subject: subj, Body: data})
	return &nats.PubAck{}, nil
}

// fakeLoader + fakeExecStore stand in for PgStore in the MatrixDispatchWorker.
type fakeLoader struct {
	task *ScheduledTask
	err  error
}

func (f *fakeLoader) LoadTask(_ context.Context, _ string) (*ScheduledTask, error) {
	return f.task, f.err
}

type fakeExecStore struct {
	id  string
	err error
}

func (f *fakeExecStore) BeginExecution(_ context.Context, _ string, _ time.Time) (string, error) {
	return f.id, f.err
}

func TestMatrixDispatchWorkerPublishesJobExecute(t *testing.T) {
	js := &fakeJetStream{}
	w := &MatrixDispatchWorker{
		JS: js,
		Loader: &fakeLoader{task: &ScheduledTask{
			TaskID:      "task-1",
			UserID:      "user-1",
			Kind:        "recurring",
			Status:      "active",
			Prompt:      "hello",
			CronExpr:    "0 9 * * 1",
			TZ:          "UTC",
			CreatedAtMs: 1700000000000,
		}},
		ExecStore: &fakeExecStore{id: "exec-1"},
	}
	err := w.Work(context.Background(), &river.Job[MatrixDispatchArgs]{
		Args: MatrixDispatchArgs{TaskID: "task-1"},
	})
	if err != nil {
		t.Fatalf("Work returned error: %v", err)
	}
	if len(js.publishes) != 1 {
		t.Fatalf("want 1 publish, got %d", len(js.publishes))
	}
	got := js.publishes[0]
	if got.Subject != SubjectJobExecute {
		t.Errorf("subject = %q, want %q", got.Subject, SubjectJobExecute)
	}
	var payload JobExecutePayload
	if jsonErr := json.Unmarshal(got.Body, &payload); jsonErr != nil {
		t.Fatalf("unmarshal: %v", jsonErr)
	}
	if payload.TaskID != "task-1" || payload.ExecutionID != "exec-1" ||
		payload.OwnerUserID != "user-1" || payload.Kind != "recurring" ||
		payload.Prompt != "hello" {
		t.Errorf("unexpected payload: %+v", payload)
	}
	if payload.FiredAtMs == 0 {
		t.Errorf("fired_at_ms should be set")
	}
}

func TestMatrixDispatchWorkerSkipsNonActiveTask(t *testing.T) {
	js := &fakeJetStream{}
	w := &MatrixDispatchWorker{
		JS: js,
		Loader: &fakeLoader{task: &ScheduledTask{
			TaskID: "task-2",
			Status: "paused",
		}},
		ExecStore: &fakeExecStore{},
	}
	err := w.Work(context.Background(), &river.Job[MatrixDispatchArgs]{
		Args: MatrixDispatchArgs{TaskID: "task-2"},
	})
	if err != nil {
		t.Fatalf("should NOT error on paused task — got %v", err)
	}
	if len(js.publishes) != 0 {
		t.Fatalf("paused task must not publish, got %d", len(js.publishes))
	}
}

func TestMatrixDispatchWorkerLoaderError(t *testing.T) {
	js := &fakeJetStream{}
	w := &MatrixDispatchWorker{
		JS:        js,
		Loader:    &fakeLoader{err: ErrTaskNotFound},
		ExecStore: &fakeExecStore{},
	}
	err := w.Work(context.Background(), &river.Job[MatrixDispatchArgs]{
		Args: MatrixDispatchArgs{TaskID: "task-missing"},
	})
	if err == nil {
		t.Fatal("expected error from loader")
	}
	if !errors.Is(err, ErrTaskNotFound) {
		t.Errorf("want wrapped ErrTaskNotFound, got %v", err)
	}
}

func TestHealthPingWorkerPublishesHeartbeat(t *testing.T) {
	js := &fakeJetStream{}
	w := &HealthPingWorker{JS: js}
	err := w.Work(context.Background(), &river.Job[HealthPingArgs]{})
	if err != nil {
		t.Fatalf("Work returned error: %v", err)
	}
	if len(js.publishes) != 1 {
		t.Fatalf("want 1 publish, got %d", len(js.publishes))
	}
	if js.publishes[0].Subject != SubjectHeartbeat {
		t.Errorf("subject = %q, want %q", js.publishes[0].Subject, SubjectHeartbeat)
	}
	var payload HeartbeatPayload
	if jsonErr := json.Unmarshal(js.publishes[0].Body, &payload); jsonErr != nil {
		t.Fatalf("unmarshal heartbeat: %v", jsonErr)
	}
	if payload.ExecutionID == "" || payload.FiredAtMs == 0 {
		t.Errorf("incomplete heartbeat: %+v", payload)
	}
}
