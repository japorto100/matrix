package contracts

type Quote struct {
	Symbol    string  `json:"symbol"`
	Exchange  string  `json:"exchange"`
	AssetType string  `json:"assetType"`
	Last      float64 `json:"last"`
	Bid       float64 `json:"bid"`
	Ask       float64 `json:"ask"`
	High      float64 `json:"high"`
	Low       float64 `json:"low"`
	Volume    float64 `json:"volume"`
	Timestamp int64   `json:"timestamp"`
	Source    string  `json:"source"`
}

type MarketEvent struct {
	Type   string `json:"type"`
	Symbol string `json:"symbol"`
}
