package contracts

type APIResponse[T any] struct {
	Success bool   `json:"success"`
	Error   string `json:"error,omitempty"`
	Data    T      `json:"data,omitempty"`
}
