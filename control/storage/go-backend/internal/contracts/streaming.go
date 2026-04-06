package contracts

type Candle struct {
	Time   int64   `json:"time"`
	Open   float64 `json:"open"`
	High   float64 `json:"high"`
	Low    float64 `json:"low"`
	Close  float64 `json:"close"`
	Volume float64 `json:"volume"`
}

type MarketStreamSnapshot struct {
	Symbol    string   `json:"symbol"`
	Exchange  string   `json:"exchange"`
	AssetType string   `json:"assetType"`
	Timeframe string   `json:"timeframe,omitempty"`
	Quote     *Quote   `json:"quote,omitempty"`
	Candle    *Candle  `json:"candle,omitempty"`
	Candles   []Candle `json:"candles,omitempty"`
	UpdatedAt string   `json:"updatedAt"`
}

type MarketAlertEvent struct {
	ID          string  `json:"id"`
	RuleID      string  `json:"ruleId,omitempty"`
	Symbol      string  `json:"symbol"`
	Condition   string  `json:"condition"`
	Target      float64 `json:"target"`
	Price       float64 `json:"price"`
	Previous    float64 `json:"previous"`
	TriggeredAt string  `json:"triggeredAt"`
	Message     string  `json:"message,omitempty"`
}
