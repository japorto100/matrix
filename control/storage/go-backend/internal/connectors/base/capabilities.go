package base

type Capabilities struct {
	Quote           bool `json:"quote,omitempty"`
	BatchQuote      bool `json:"batchQuote,omitempty"`
	OHLCV           bool `json:"ohlcv,omitempty"`
	Depth           bool `json:"depth,omitempty"`
	Search          bool `json:"search,omitempty"`
	News            bool `json:"news,omitempty"`
	Streaming       bool `json:"streaming,omitempty"`
	OrderPlacement  bool `json:"orderPlacement,omitempty"`
	OrderStatus     bool `json:"orderStatus,omitempty"`
	Backfill        bool `json:"backfill,omitempty"`
	RequiresAPIKey  bool `json:"requiresApiKey,omitempty"`
	SupportsSandbox bool `json:"supportsSandbox,omitempty"`
}

func (c Capabilities) SupportsRealtime() bool {
	return c.Streaming || c.Quote || c.BatchQuote
}

func (c Capabilities) SupportsAnalyticsSeed() bool {
	return c.OHLCV || c.News
}

type MarketCapabilities struct {
	Quote      bool
	BatchQuote bool
	OHLCV      bool
	Depth      bool
	Search     bool
	News       bool
}

type StreamCapabilities struct {
	Live bool
}

type OrderCapabilities struct {
	Submit bool
	Status bool
}

type AccountCapabilities struct {
	RequiresAPIKey bool
	Sandbox        bool
}

func (c Capabilities) Market() MarketCapabilities {
	return MarketCapabilities{
		Quote:      c.Quote,
		BatchQuote: c.BatchQuote,
		OHLCV:      c.OHLCV,
		Depth:      c.Depth,
		Search:     c.Search,
		News:       c.News,
	}
}

func (c Capabilities) Stream() StreamCapabilities {
	return StreamCapabilities{Live: c.Streaming}
}

func (c Capabilities) Order() OrderCapabilities {
	return OrderCapabilities{
		Submit: c.OrderPlacement,
		Status: c.OrderStatus,
	}
}

func (c Capabilities) Account() AccountCapabilities {
	return AccountCapabilities{
		RequiresAPIKey: c.RequiresAPIKey,
		Sandbox:        c.SupportsSandbox,
	}
}

type ProviderDescriptor struct {
	Name               string       `json:"name"`
	Group              string       `json:"group,omitempty"`
	Kind               string       `json:"kind,omitempty"`
	AuthMode           string       `json:"authMode,omitempty"`
	Bridge             string       `json:"bridge,omitempty"`
	Notes              string       `json:"notes,omitempty"`
	Enabled            bool         `json:"enabled"`
	RateLimitPerSecond float64      `json:"rateLimitPerSecond,omitempty"`
	RateLimitBurst     int          `json:"rateLimitBurst,omitempty"`
	RetryProfile       string       `json:"retryProfile,omitempty"`
	Fallbacks          []string     `json:"fallbacks,omitempty"`
	Capabilities       Capabilities `json:"capabilities,omitzero"`
}
