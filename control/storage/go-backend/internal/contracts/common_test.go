package contracts

import "testing"

func TestAPIResponseGenericDataRoundTrip(t *testing.T) {
	resp := APIResponse[int]{
		Success: true,
		Data:    42,
	}

	if !resp.Success {
		t.Fatal("expected success to be true")
	}
	if resp.Data != 42 {
		t.Fatalf("expected data 42, got %d", resp.Data)
	}
}
