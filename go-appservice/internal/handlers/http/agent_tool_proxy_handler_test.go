package http

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type fakeToolClient struct {
	getStatus int
	getBody   []byte
	getErr    error
	postStatus int
	postBody   []byte
	postErr    error
}

func (c *fakeToolClient) Get(_ context.Context, _ string) (int, []byte, error) {
	return c.getStatus, c.getBody, c.getErr
}
func (c *fakeToolClient) Post(_ context.Context, _ string, _ []byte) (int, []byte, error) {
	return c.postStatus, c.postBody, c.postErr
}

func TestAgentToolProxyHandler_GETSuccess(t *testing.T) {
	client := &fakeToolClient{getStatus: 200, getBody: []byte(`{"chart":"data"}`)}
	h := AgentToolProxyHandler(client, "/api/v1/agent/tools/chart-state")
	req := httptest.NewRequest(http.MethodGet, "/api/v1/agent/tools/chart-state", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "chart") {
		t.Errorf("body = %q", rec.Body.String())
	}
}

func TestAgentToolProxyHandler_MethodNotAllowed(t *testing.T) {
	client := &fakeToolClient{}
	h := AgentToolProxyHandler(client, "/test")
	req := httptest.NewRequest(http.MethodPost, "/test", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestAgentToolProxyHandler_NilClient(t *testing.T) {
	h := AgentToolProxyHandler(nil, "/test")
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want 503", rec.Code)
	}
}

func TestAgentMutationProxyHandler_POSTSuccess(t *testing.T) {
	client := &fakeToolClient{postStatus: 200, postBody: []byte(`{"ok":true}`)}
	h := AgentMutationProxyHandler(client, "/api/v1/agent/tools/set_chart_state")
	req := httptest.NewRequest(http.MethodPost, "/test", strings.NewReader(`{"state":"new"}`))
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}

func TestAgentMutationProxyHandler_MethodNotAllowed(t *testing.T) {
	client := &fakeToolClient{}
	h := AgentMutationProxyHandler(client, "/test")
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestAgentMutationProxyHandler_NilClient(t *testing.T) {
	h := AgentMutationProxyHandler(nil, "/test")
	req := httptest.NewRequest(http.MethodPost, "/test", strings.NewReader("{}"))
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want 503", rec.Code)
	}
}
