package contracts

type PortfolioSnapshot struct {
	Equity      float64 `json:"equity"`
	TotalPnL    float64 `json:"totalPnl"`
	MaxDrawdown float64 `json:"maxDrawdown"`
}
