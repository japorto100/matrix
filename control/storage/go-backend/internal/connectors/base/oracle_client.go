package base

import (
	"context"
	"fmt"
	"time"
)

type OracleQuote struct {
	Symbol      string    `json:"symbol"`
	Price       float64   `json:"price"`
	Timestamp   time.Time `json:"timestamp"`
	Source      string    `json:"source"`
	Confidence  float64   `json:"confidence,omitempty"`
	Verified    bool      `json:"verified"`
	ChainID     string    `json:"chainId,omitempty"`
	FeedAddress string    `json:"feedAddress,omitempty"`
}

type OracleClient interface {
	GetQuote(ctx context.Context, symbol string) (*OracleQuote, error)
}

type OracleDisagreement struct {
	Symbol       string    `json:"symbol"`
	Web2Source   string    `json:"web2Source"`
	OracleSource string    `json:"oracleSource"`
	Web2Price    float64   `json:"web2Price"`
	OraclePrice  float64   `json:"oraclePrice"`
	BpsGap       float64   `json:"bpsGap"`
	DetectedAt   time.Time `json:"detectedAt"`
}

func ComputeOracleDisagreement(symbol string, web2Source string, web2Price float64, oracle *OracleQuote) *OracleDisagreement {
	if oracle == nil || web2Price <= 0 || oracle.Price <= 0 {
		return nil
	}
	gap := ((oracle.Price - web2Price) / web2Price) * 10000
	if gap < 0 {
		gap = -gap
	}
	return &OracleDisagreement{
		Symbol:       symbol,
		Web2Source:   web2Source,
		OracleSource: oracle.Source,
		Web2Price:    web2Price,
		OraclePrice:  oracle.Price,
		BpsGap:       gap,
		DetectedAt:   time.Now().UTC(),
	}
}

type ErrOracleNotImplemented struct {
	Provider string
}

func (e ErrOracleNotImplemented) Error() string {
	if e.Provider == "" {
		return "oracle connector not implemented"
	}
	return fmt.Sprintf("oracle connector not implemented: %s", e.Provider)
}
