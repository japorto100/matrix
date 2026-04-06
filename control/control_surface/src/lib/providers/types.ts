// Market Data Provider Types
// Based on research: Alpha Vantage, Finnhub, Twelve Data, ECB

export type AssetType = "stock" | "crypto" | "fx" | "index" | "etf" | "commodity" | "macro";
export type TimeframeValue =
	| "1m"
	| "3m"
	| "5m"
	| "15m"
	| "30m"
	| "1H"
	| "2H"
	| "4H"
	| "1D"
	| "1W"
	| "1M";

export interface OHLCVData {
	time: number;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
}

export interface SymbolResult {
	symbol: string;
	name: string;
	type: AssetType;
	exchange?: string;
	currency?: string;
}

export interface QuoteData {
	symbol: string;
	price: number;
	change: number;
	changePercent: number;
	high: number;
	low: number;
	open: number;
	volume: number;
	timestamp: number;
}

export interface ProviderInfo {
	name: string;
	displayName: string;
	supportedAssets: AssetType[];
	requiresAuth: boolean;
	rateLimit: {
		requests: number;
		period: string;
	};
	freePlan: boolean;
	documentation: string;
}

export interface OHLCVRequestOptions {
	start?: number;
	end?: number;
}

export interface MarketDataProvider {
	readonly info: ProviderInfo;

	// Core Methods
	fetchOHLCV(
		symbol: string,
		timeframe: TimeframeValue,
		limit?: number,
		options?: OHLCVRequestOptions,
	): Promise<OHLCVData[]>;

	searchSymbols(query: string): Promise<SymbolResult[]>;

	getQuote(symbol: string): Promise<QuoteData>;

	// Optional Methods
	isAvailable(): Promise<boolean>;
}

// Provider Registry
export const PROVIDER_REGISTRY: Record<string, ProviderInfo> = {
	alphavantage: {
		name: "alphavantage",
		displayName: "Alpha Vantage",
		supportedAssets: ["stock", "fx", "crypto", "index"],
		requiresAuth: true,
		rateLimit: { requests: 25, period: "day" },
		freePlan: true,
		documentation: "https://www.alphavantage.co/documentation/",
	},
	finnhub: {
		name: "finnhub",
		displayName: "Finnhub",
		supportedAssets: ["stock", "crypto", "fx"],
		requiresAuth: true,
		rateLimit: { requests: 60, period: "minute" },
		freePlan: true,
		documentation: "https://finnhub.io/docs/api",
	},
	twelvedata: {
		name: "twelvedata",
		displayName: "Twelve Data",
		supportedAssets: ["stock", "etf", "fx", "crypto", "index"],
		requiresAuth: true,
		rateLimit: { requests: 800, period: "day" },
		freePlan: true,
		documentation: "https://twelvedata.com/docs",
	},
	yahoo: {
		name: "yahoo",
		displayName: "Yahoo Finance (Unofficial)",
		supportedAssets: ["stock", "etf", "fx", "crypto", "index", "commodity"],
		requiresAuth: false,
		rateLimit: { requests: 100, period: "minute" },
		freePlan: true,
		documentation: "https://query1.finance.yahoo.com (unofficial endpoints)",
	},
	yfinance: {
		name: "yfinance",
		displayName: "yfinance Bridge (Unofficial Wrapper)",
		supportedAssets: ["stock", "etf", "fx", "crypto", "index", "commodity"],
		requiresAuth: false,
		rateLimit: { requests: 60, period: "minute" },
		freePlan: true,
		documentation: "https://ranaroussi.github.io/yfinance/",
	},
	fmp: {
		name: "fmp",
		displayName: "Financial Modeling Prep",
		supportedAssets: ["stock", "etf", "index"],
		requiresAuth: true,
		rateLimit: { requests: 250, period: "day" },
		freePlan: true,
		documentation: "https://site.financialmodelingprep.com/developer/docs",
	},
	eodhd: {
		name: "eodhd",
		displayName: "EODHD",
		supportedAssets: ["stock", "etf", "fx", "index", "commodity"],
		requiresAuth: true,
		rateLimit: { requests: 20, period: "day" },
		freePlan: true,
		documentation: "https://eodhd.com/financial-apis",
	},
	marketstack: {
		name: "marketstack",
		displayName: "Marketstack",
		supportedAssets: ["stock", "etf", "index"],
		requiresAuth: true,
		rateLimit: { requests: 100, period: "month" },
		freePlan: true,
		documentation: "https://marketstack.com/documentation",
	},
	polygon: {
		name: "polygon",
		displayName: "Polygon.io",
		supportedAssets: ["stock", "fx", "crypto", "index"],
		requiresAuth: true,
		rateLimit: { requests: 5, period: "minute" },
		freePlan: true,
		documentation: "https://polygon.io/docs",
	},
	coinmarketcap: {
		name: "coinmarketcap",
		displayName: "CoinMarketCap",
		supportedAssets: ["crypto"],
		requiresAuth: true,
		rateLimit: { requests: 30, period: "minute" },
		freePlan: true,
		documentation: "https://coinmarketcap.com/api/documentation/v1/",
	},
	ccxt: {
		name: "ccxt",
		displayName: "CCXT (Crypto Fallback)",
		supportedAssets: ["crypto"],
		requiresAuth: false,
		rateLimit: { requests: 20, period: "minute" },
		freePlan: true,
		documentation: "https://docs.ccxt.com/",
	},
	finage: {
		name: "finage",
		displayName: "Finage",
		supportedAssets: ["stock", "etf", "fx", "crypto", "index"],
		requiresAuth: true,
		rateLimit: { requests: 60, period: "minute" },
		freePlan: true,
		documentation: "https://finage.co.uk/product/stocks",
	},
	fred: {
		name: "fred",
		displayName: "FRED (St. Louis Fed)",
		supportedAssets: ["index"],
		requiresAuth: true,
		rateLimit: { requests: 1000000, period: "day" },
		freePlan: true,
		documentation: "https://fred.stlouisfed.org/docs/api/fred/",
	},
	banxico: {
		name: "banxico",
		displayName: "Banco de México (SIE API)",
		supportedAssets: ["macro", "fx"],
		requiresAuth: true,
		rateLimit: { requests: 100, period: "minute" },
		freePlan: true,
		documentation: "https://www.banxico.org.mx/SieAPIRest/service/v1/",
	},
	bok: {
		name: "bok",
		displayName: "Bank of Korea (ECOS Open API)",
		supportedAssets: ["macro"],
		requiresAuth: true,
		rateLimit: { requests: 100, period: "minute" },
		freePlan: true,
		documentation: "https://ecos.bok.or.kr/api/",
	},
	ecb: {
		name: "ecb",
		displayName: "European Central Bank",
		supportedAssets: ["fx"],
		requiresAuth: false,
		rateLimit: { requests: 100, period: "day" },
		freePlan: true,
		documentation: "https://data-api.ecb.europa.eu/help",
	},
	imf: {
		name: "imf",
		displayName: "IMF IFS (International Financial Statistics)",
		supportedAssets: ["macro"],
		requiresAuth: false,
		rateLimit: { requests: 10, period: "5 seconds" },
		freePlan: true,
		documentation:
			"https://datahelp.imf.org/knowledgebase/articles/667681-json-restful-web-service",
	},
	demo: {
		name: "demo",
		displayName: "Demo Data",
		supportedAssets: ["stock", "crypto", "fx", "index", "etf", "commodity"],
		requiresAuth: false,
		rateLimit: { requests: 999999, period: "day" },
		freePlan: true,
		documentation: "Internal demo data generator",
	},
};

// Timeframe Mapping for different APIs
export const TIMEFRAME_MAP: Record<string, Record<TimeframeValue, string>> = {
	alphavantage: {
		"1m": "1min",
		"3m": "1min", // Fallback
		"5m": "5min",
		"15m": "15min",
		"30m": "30min",
		"1H": "60min",
		"2H": "60min", // Fallback
		"4H": "60min", // Alpha Vantage doesn't support 4H
		"1D": "daily",
		"1W": "weekly",
		"1M": "monthly",
	},
	finnhub: {
		"1m": "1",
		"3m": "1", // Fallback
		"5m": "5",
		"15m": "15",
		"30m": "30",
		"1H": "60",
		"2H": "120",
		"4H": "240",
		"1D": "D",
		"1W": "W",
		"1M": "M",
	},
	twelvedata: {
		"1m": "1min",
		"3m": "3min",
		"5m": "5min",
		"15m": "15min",
		"30m": "30min",
		"1H": "1h",
		"2H": "2h",
		"4H": "4h",
		"1D": "1day",
		"1W": "1week",
		"1M": "1month",
	},
	yahoo: {
		"1m": "1m",
		"3m": "2m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "60m",
		"2H": "1h", // Fallback
		"4H": "1h",
		"1D": "1d",
		"1W": "1wk",
		"1M": "1mo",
	},
	yfinance: {
		"1m": "1m",
		"3m": "2m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "60m",
		"2H": "1h", // Fallback
		"4H": "1h",
		"1D": "1d",
		"1W": "1wk",
		"1M": "1mo",
	},
	fmp: {
		"1m": "1min",
		"3m": "1min", // Fallback
		"5m": "5min",
		"15m": "15min",
		"30m": "30min",
		"1H": "1hour",
		"2H": "1hour", // Fallback
		"4H": "4hour",
		"1D": "1day",
		"1W": "1week",
		"1M": "1month",
	},
	eodhd: {
		"1m": "1m",
		"3m": "1m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "1h",
		"2H": "1h", // Fallback
		"4H": "4h",
		"1D": "d",
		"1W": "w",
		"1M": "m",
	},
	marketstack: {
		"1m": "N/A",
		"3m": "N/A",
		"5m": "N/A",
		"15m": "N/A",
		"30m": "N/A",
		"1H": "N/A",
		"2H": "N/A",
		"4H": "N/A",
		"1D": "daily",
		"1W": "weekly",
		"1M": "monthly",
	},
	polygon: {
		"1m": "1/minute",
		"3m": "1/minute", // Fallback
		"5m": "5/minute",
		"15m": "15/minute",
		"30m": "30/minute",
		"1H": "1/hour",
		"2H": "1/hour", // Fallback
		"4H": "4/hour",
		"1D": "1/day",
		"1W": "1/week",
		"1M": "1/month",
	},
	coinmarketcap: {
		"1m": "1m",
		"3m": "1m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "1h",
		"2H": "1h", // Fallback
		"4H": "4h",
		"1D": "1d",
		"1W": "7d",
		"1M": "30d",
	},
	ccxt: {
		"1m": "1m",
		"3m": "1m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "1h",
		"2H": "2h",
		"4H": "4h",
		"1D": "1d",
		"1W": "1w",
		"1M": "1M",
	},
	finage: {
		"1m": "1m",
		"3m": "1m", // Fallback
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "1h",
		"2H": "2h",
		"4H": "4h",
		"1D": "1d",
		"1W": "1w",
		"1M": "1mo",
	},
	fred: {
		"1m": "N/A",
		"3m": "N/A",
		"5m": "N/A",
		"15m": "N/A",
		"30m": "N/A",
		"1H": "N/A",
		"2H": "N/A",
		"4H": "N/A",
		"1D": "d",
		"1W": "w",
		"1M": "m",
	},
	ecb: {
		"1D": "D",
		"1W": "W",
		"1M": "M",
		"1m": "D",
		"3m": "D",
		"5m": "D",
		"15m": "D",
		"30m": "D",
		"1H": "D",
		"2H": "D",
		"4H": "D",
	},
	demo: {
		"1m": "1m",
		"3m": "3m",
		"5m": "5m",
		"15m": "15m",
		"30m": "30m",
		"1H": "1H",
		"2H": "2H",
		"4H": "4H",
		"1D": "1D",
		"1W": "1W",
		"1M": "1M",
	},
};
