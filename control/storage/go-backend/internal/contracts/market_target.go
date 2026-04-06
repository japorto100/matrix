package contracts

import "strings"

type Pair struct {
	Base  string `json:"base"`
	Quote string `json:"quote"`
}

func (p Pair) Normalized() Pair {
	return Pair{
		Base:  normalizeMarketToken(p.Base, true),
		Quote: normalizeMarketToken(p.Quote, true),
	}
}

func (p Pair) Symbol() string {
	normalized := p.Normalized()
	if normalized.Base == "" {
		return ""
	}
	if normalized.Quote == "" {
		return normalized.Base
	}
	return normalized.Base + "/" + normalized.Quote
}

type MarketTarget struct {
	Exchange  string `json:"exchange"`
	AssetType string `json:"assetType"`
	Pair      Pair   `json:"pair"`
}

func (t MarketTarget) Normalized() MarketTarget {
	return MarketTarget{
		Exchange:  strings.TrimSpace(t.Exchange),
		AssetType: normalizeMarketToken(t.AssetType, false),
		Pair:      t.Pair.Normalized(),
	}
}

func (t MarketTarget) Symbol() string {
	return t.Pair.Symbol()
}

type OrderbookLevel struct {
	Price  float64 `json:"price"`
	Amount float64 `json:"amount"`
	ID     int64   `json:"id,omitempty"`
}

type OrderbookSnapshot struct {
	Exchange  string           `json:"exchange"`
	AssetType string           `json:"assetType"`
	Pair      Pair             `json:"pair"`
	Bids      []OrderbookLevel `json:"bids"`
	Asks      []OrderbookLevel `json:"asks"`
	Timestamp int64            `json:"timestamp"`
	Source    string           `json:"source"`
}

func (s OrderbookSnapshot) Symbol() string {
	return s.Pair.Symbol()
}

func (s OrderbookSnapshot) BestBid() (OrderbookLevel, bool) {
	if len(s.Bids) == 0 {
		return OrderbookLevel{}, false
	}
	return s.Bids[0], true
}

func (s OrderbookSnapshot) BestAsk() (OrderbookLevel, bool) {
	if len(s.Asks) == 0 {
		return OrderbookLevel{}, false
	}
	return s.Asks[0], true
}

func normalizeMarketToken(value string, upper bool) string {
	normalized := strings.TrimSpace(value)
	if upper {
		return strings.ToUpper(normalized)
	}
	return strings.ToLower(normalized)
}
