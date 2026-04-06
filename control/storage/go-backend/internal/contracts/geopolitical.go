package contracts

type GeopoliticalEvent struct {
	ID           string  `json:"id"`
	URL          string  `json:"url,omitempty"`
	EventDate    string  `json:"eventDate"`
	Country      string  `json:"country"`
	Region       string  `json:"region,omitempty"`
	EventType    string  `json:"eventType"`
	SubEventType string  `json:"subEventType"`
	Actor1       string  `json:"actor1"`
	Actor2       string  `json:"actor2"`
	Fatalities   int     `json:"fatalities"`
	Location     string  `json:"location"`
	Latitude     float64 `json:"latitude"`
	Longitude    float64 `json:"longitude"`
	Source       string  `json:"source"`
	Notes        string  `json:"notes"`
}

type GeopoliticalEventsFilters struct {
	Source       string `json:"source,omitempty"`
	Country      string `json:"country,omitempty"`
	Region       string `json:"region,omitempty"`
	EventType    string `json:"eventType,omitempty"`
	SubEventType string `json:"subEventType,omitempty"`
	StartDate    string `json:"startDate,omitempty"`
	EndDate      string `json:"endDate,omitempty"`
	Limit        int    `json:"limit"`
}

type GeopoliticalEventsData struct {
	Source  string                    `json:"source"`
	Filters GeopoliticalEventsFilters `json:"filters"`
	Items   []GeopoliticalEvent       `json:"items"`
}

type GeopoliticalContextItem struct {
	ID          string `json:"id"`
	Source      string `json:"source"`
	Title       string `json:"title"`
	URL         string `json:"url"`
	Summary     string `json:"summary,omitempty"`
	PublishedAt string `json:"publishedAt,omitempty"`
	Region      string `json:"region,omitempty"`
}

type GeopoliticalContextFilters struct {
	Source string `json:"source"`
	Query  string `json:"query,omitempty"`
	Region string `json:"region,omitempty"`
	Limit  int    `json:"limit"`
}

type GeopoliticalContextData struct {
	Source  string                     `json:"source"`
	Filters GeopoliticalContextFilters `json:"filters"`
	Items   []GeopoliticalContextItem  `json:"items"`
}

type GeopoliticalGameTheoryImpactItem struct {
	ID          string   `json:"id"`
	EventID     string   `json:"eventId"`
	EventTitle  string   `json:"eventTitle"`
	Region      string   `json:"region"`
	MarketBias  string   `json:"marketBias"`
	ImpactScore float64  `json:"impactScore"`
	Confidence  float64  `json:"confidence"`
	Drivers     []string `json:"drivers"`
	Symbols     []string `json:"symbols"`
	EventDate   string   `json:"eventDate"`
}

type GeopoliticalGameTheorySummary struct {
	AnalyzedEvents int     `json:"analyzedEvents"`
	AvgImpactScore float64 `json:"avgImpactScore"`
	RiskOnCount    int     `json:"riskOnCount"`
	RiskOffCount   int     `json:"riskOffCount"`
	NeutralCount   int     `json:"neutralCount"`
	TopRegion      string  `json:"topRegion,omitempty"`
}

type GeopoliticalGameTheoryFilters struct {
	Country      string `json:"country,omitempty"`
	Region       string `json:"region,omitempty"`
	EventType    string `json:"eventType,omitempty"`
	SubEventType string `json:"subEventType,omitempty"`
	StartDate    string `json:"startDate,omitempty"`
	EndDate      string `json:"endDate,omitempty"`
	Limit        int    `json:"limit"`
}

type GeopoliticalGameTheoryData struct {
	Source  string                             `json:"source"`
	Filters GeopoliticalGameTheoryFilters      `json:"filters"`
	Summary GeopoliticalGameTheorySummary      `json:"summary"`
	Items   []GeopoliticalGameTheoryImpactItem `json:"items"`
}
