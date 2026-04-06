package contracts

type Order struct {
	ID       string  `json:"id"`
	Symbol   string  `json:"symbol"`
	Side     string  `json:"side"`
	Quantity float64 `json:"quantity"`
	Status   string  `json:"status"`
}
