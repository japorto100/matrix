package app

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	otelhttp "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

	"tradeviewfusion/go-backend/internal/appstate"
	"tradeviewfusion/go-backend/internal/auditjsonl"
	"tradeviewfusion/go-backend/internal/cache"
	"tradeviewfusion/go-backend/internal/capability"
	"tradeviewfusion/go-backend/internal/connectors/acled"
	"tradeviewfusion/go-backend/internal/connectors/adb"
	"tradeviewfusion/go-backend/internal/connectors/agentservice"
	"tradeviewfusion/go-backend/internal/connectors/banxico"
	"tradeviewfusion/go-backend/internal/connectors/bcb"
	"tradeviewfusion/go-backend/internal/connectors/bcra"
	"tradeviewfusion/go-backend/internal/connectors/bok"
	"tradeviewfusion/go-backend/internal/connectors/cfr"
	"tradeviewfusion/go-backend/internal/connectors/crisiswatch"
	"tradeviewfusion/go-backend/internal/connectors/ecb"
	"tradeviewfusion/go-backend/internal/connectors/finnhub"
	"tradeviewfusion/go-backend/internal/connectors/fred"
	"tradeviewfusion/go-backend/internal/connectors/gametheory"
	"tradeviewfusion/go-backend/internal/connectors/gct"
	"tradeviewfusion/go-backend/internal/connectors/gdelt"
	geomapsources "tradeviewfusion/go-backend/internal/connectors/geomapsources"
	geopoliticalnext "tradeviewfusion/go-backend/internal/connectors/geopoliticalnext"
	"tradeviewfusion/go-backend/internal/connectors/imf"
	indicatorservice "tradeviewfusion/go-backend/internal/connectors/indicatorservice"
	"tradeviewfusion/go-backend/internal/connectors/memory"
	newsConnectors "tradeviewfusion/go-backend/internal/connectors/news"
	"tradeviewfusion/go-backend/internal/connectors/nyfed"
	"tradeviewfusion/go-backend/internal/connectors/oecd"
	"tradeviewfusion/go-backend/internal/connectors/ofr"
	"tradeviewfusion/go-backend/internal/connectors/rbi"
	connectorregistry "tradeviewfusion/go-backend/internal/connectors/registry"
	softsignals "tradeviewfusion/go-backend/internal/connectors/softsignals"
	"tradeviewfusion/go-backend/internal/connectors/symbolcatalog"
	"tradeviewfusion/go-backend/internal/connectors/tcmb"
	"tradeviewfusion/go-backend/internal/connectors/un"
	"tradeviewfusion/go-backend/internal/connectors/worldbank"
	"tradeviewfusion/go-backend/internal/connectors/yahoo"
	httpHandlers "tradeviewfusion/go-backend/internal/handlers/http"
	sseHandlers "tradeviewfusion/go-backend/internal/handlers/sse"
	"tradeviewfusion/go-backend/internal/messaging"
	"tradeviewfusion/go-backend/internal/observability"
	"tradeviewfusion/go-backend/internal/router/adaptive"
	backtestServices "tradeviewfusion/go-backend/internal/services/backtest"
	geopoliticalServices "tradeviewfusion/go-backend/internal/services/geopolitical"
	marketServices "tradeviewfusion/go-backend/internal/services/market"
	"tradeviewfusion/go-backend/internal/storage"
)

func NewServerFromEnv() (*Server, error) {
	host := envOr("GATEWAY_HOST", "127.0.0.1")
	port := envOr("GATEWAY_PORT", "9060")
	secureEnv, err := secureEnvDecoderFromEnv()
	if err != nil {
		return nil, err
	}
	gctUsername, err := secureEnv.decodeStringValue("GCT_USERNAME", "GCT_USERNAME_ENC", "replace-me")
	if err != nil {
		return nil, err
	}
	gctPassword, err := secureEnv.decodeStringValue("GCT_PASSWORD", "GCT_PASSWORD_ENC", "replace-me")
	if err != nil {
		return nil, err
	}
	gctBacktestUsername, err := secureEnv.decodeStringValue("GCT_BACKTEST_USERNAME", "GCT_BACKTEST_USERNAME_ENC", gctUsername)
	if err != nil {
		return nil, err
	}
	gctBacktestPassword, err := secureEnv.decodeStringValue("GCT_BACKTEST_PASSWORD", "GCT_BACKTEST_PASSWORD_ENC", gctPassword)
	if err != nil {
		return nil, err
	}

	gctConfig := gct.Config{
		GrpcAddress:          envOr("GCT_GRPC_ADDRESS", "127.0.0.1:9052"),
		JsonRPCAddress:       envOr("GCT_JSONRPC_ADDRESS", "127.0.0.1:9053"),
		Username:             gctUsername,
		Password:             gctPassword,
		RequestTimeout:       durationMsOr("GCT_HTTP_TIMEOUT_MS", 4000),
		RetryCount:           intOr("GCT_HTTP_RETRIES", 1),
		InsecureSkipVerifyTL: boolOr("GCT_JSONRPC_INSECURE_TLS", false),
		PreferGRPC:           boolOr("GCT_PREFER_GRPC", true),
	}
	if validationErr := validateGCTSecurityConfig(gctConfig, gctSecurityPolicyFromEnv()); validationErr != nil {
		return nil, validationErr
	}
	gctClient := gct.NewClient(gctConfig)
	ecbClient := ecb.NewClient(ecb.Config{
		RatesURL:       envOr("ECB_RATES_URL", ecb.DefaultRatesURL),
		RequestTimeout: durationMsOr("ECB_HTTP_TIMEOUT_MS", 4000),
	})
	finnhubClient := finnhub.NewClient(finnhub.Config{
		BaseURL:        envOr("FINNHUB_BASE_URL", finnhub.DefaultBaseURL),
		WSBaseURL:      envOr("FINNHUB_WS_BASE_URL", finnhub.DefaultWSBaseURL),
		APIKey:         envOr("FINNHUB_API_KEY", ""),
		RequestTimeout: durationMsOr("FINNHUB_HTTP_TIMEOUT_MS", 4000),
		CacheTTL:       durationMsOr("FINNHUB_CACHE_TTL_MS", 15000),
	})
	fredClient := fred.NewClient(fred.Config{
		BaseURL:        envOr("FRED_BASE_URL", fred.DefaultBaseURL),
		APIKey:         envOr("FRED_API_KEY", ""),
		RequestTimeout: durationMsOr("FRED_HTTP_TIMEOUT_MS", 4000),
		CacheTTL:       durationMsOr("FRED_CACHE_TTL_MS", 300000),
	})
	bcbClient := bcb.NewClient(bcb.Config{
		BaseURL:        envOr("BCB_BASE_URL", bcb.DefaultBaseURL),
		RequestTimeout: durationMsOr("BCB_HTTP_TIMEOUT_MS", 4000),
	})
	banxicoClient := banxico.NewClient(banxico.Config{
		BaseURL:        envOr("BANXICO_BASE_URL", banxico.DefaultBaseURL),
		APIToken:       envOr("BANXICO_API_TOKEN", ""),
		RequestTimeout: durationMsOr("BANXICO_HTTP_TIMEOUT_MS", 4000),
		CacheTTL:       durationMsOr("BANXICO_CACHE_TTL_MS", 300000),
	})
	bokClient := bok.NewClient(bok.Config{
		BaseURL:        envOr("BOK_ECOS_BASE_URL", bok.DefaultBaseURL),
		APIKey:         envOr("BOK_ECOS_API_KEY", ""),
		RequestTimeout: durationMsOr("BOK_ECOS_HTTP_TIMEOUT_MS", 4000),
		CacheTTL:       durationMsOr("BOK_ECOS_CACHE_TTL_MS", 300000),
	})
	bcraClient := bcra.NewClient(bcra.Config{
		BaseURL:        envOr("BCRA_BASE_URL", bcra.DefaultBaseURL),
		RequestTimeout: durationMsOr("BCRA_HTTP_TIMEOUT_MS", 4000),
	})
	tcmbClient := tcmb.NewClient(tcmb.Config{
		BaseURL:        envOr("TCMB_EVDS_BASE_URL", tcmb.DefaultBaseURL),
		RequestTimeout: durationMsOr("TCMB_EVDS_HTTP_TIMEOUT_MS", 4000),
	})
	rbiClient := rbi.NewClient(rbi.Config{
		BaseURL:        envOr("RBI_DBIE_BASE_URL", rbi.DefaultBaseURL),
		RequestTimeout: durationMsOr("RBI_DBIE_HTTP_TIMEOUT_MS", 5000),
	})
	imfClient := imf.NewClient(imf.Config{
		BaseURL:        envOr("IMF_BASE_URL", imf.DefaultBaseURL),
		RequestTimeout: durationMsOr("IMF_HTTP_TIMEOUT_MS", 6000),
	})
	macroClient := marketServices.NewRoutedMacroClient(fredClient, bcbClient)
	macroClient.RegisterProviderPrefixClient("banxico", "BANXICO_", banxicoClient)
	macroClient.RegisterProviderPrefixClient("bok", "BOK_ECOS_", bokClient)
	macroClient.RegisterProviderPrefixClient("bcra", "BCRA_", bcraClient)
	macroClient.RegisterProviderPrefixClient("tcmb", "TCMB_EVDS_", tcmbClient)
	macroClient.RegisterProviderPrefixClient("rbi", "RBI_DBIE_FXRES_", rbiClient)
	macroClient.RegisterProviderPrefixClient("imf", "IMF_IFS_", imfClient)
	oecdClient := oecd.NewClient(oecd.Config{
		BaseURL:        envOr("OECD_BASE_URL", oecd.DefaultBaseURL),
		RequestTimeout: durationMsOr("OECD_HTTP_TIMEOUT_MS", 6000),
	})
	macroClient.RegisterProviderPrefixClient("oecd", "OECD_", oecdClient)
	worldbankClient := worldbank.NewClient(worldbank.Config{
		BaseURL:        envOr("WORLDBANK_BASE_URL", worldbank.DefaultBaseURL),
		RequestTimeout: durationMsOr("WORLDBANK_HTTP_TIMEOUT_MS", 6000),
	})
	macroClient.RegisterProviderPrefixClient("worldbank", "WB_WDI_", worldbankClient)
	unClient := un.NewClient(un.Config{
		BaseURL:        envOr("UN_BASE_URL", un.DefaultBaseURL),
		RequestTimeout: durationMsOr("UN_HTTP_TIMEOUT_MS", 6000),
	})
	macroClient.RegisterProviderPrefixClient("un", "UN_", unClient)
	adbClient := adb.NewClient(adb.Config{
		BaseURL:        envOr("ADB_BASE_URL", adb.DefaultBaseURL),
		RequestTimeout: durationMsOr("ADB_HTTP_TIMEOUT_MS", 6000),
	})
	macroClient.RegisterProviderPrefixClient("adb", "ADB_", adbClient)
	ofrClient := ofr.NewClient(ofr.Config{
		BaseURL:        envOr("OFR_BASE_URL", ofr.DefaultBaseURL),
		RequestTimeout: durationMsOr("OFR_HTTP_TIMEOUT_MS", 6000),
		CacheTTL:       durationMsOr("OFR_CACHE_TTL_MS", 300000),
	})
	macroClient.RegisterProviderPrefixClient("ofr", "OFR_", ofrClient)
	nyfedClient := nyfed.NewClient(nyfed.Config{
		BaseURL:        envOr("NYFED_BASE_URL", nyfed.DefaultBaseURL),
		RequestTimeout: durationMsOr("NYFED_HTTP_TIMEOUT_MS", 6000),
		CacheTTL:       durationMsOr("NYFED_CACHE_TTL_MS", 300000),
	})
	macroClient.RegisterProviderPrefixClient("nyfed", "NYFED_", nyfedClient)
	connectorRegistry, connectorRegistryErr := loadConnectorRegistry()
	if connectorRegistryErr != nil && boolOr("ADAPTIVE_ROUTER_REQUIRED", false) {
		return nil, connectorRegistryErr
	}
	yahooClient := yahoo.NewClient(yahoo.Config{
		BaseURL:        envOr("YAHOO_BASE_URL", yahoo.DefaultBaseURL),
		RequestTimeout: durationMsOr("YAHOO_HTTP_TIMEOUT_MS", 5000),
		Registry:       connectorRegistry,
	})
	indicatorServiceClient := indicatorservice.NewClient(indicatorservice.Config{
		BaseURL:        envOr("INDICATOR_SERVICE_URL", indicatorservice.DefaultBaseURL),
		RequestTimeout: durationMsOr("INDICATOR_SERVICE_TIMEOUT_MS", 8000),
		Registry:       connectorRegistry,
	})
	softSignalsProxyClient := softsignals.NewClient(softsignals.Config{
		BaseURL:        envOr("GEOPOLITICAL_SOFT_SIGNAL_URL", softsignals.DefaultBaseURL),
		RequestTimeout: durationMsOr("GEOPOLITICAL_SOFT_SIGNAL_TIMEOUT_MS", 8000),
	})
	symbolCatalogClient := symbolcatalog.NewClient(symbolcatalog.Config{
		RegistryPath: envOr("SYMBOL_CATALOG_REGISTRY_PATH", ""),
		Registry:     connectorRegistry,
	})
	geopoliticalNextClient := geopoliticalnext.NewClient(geopoliticalnext.Config{
		BaseURL:        envOr("GEOPOLITICAL_FRONTEND_API_URL", geopoliticalnext.DefaultBaseURL),
		RequestTimeout: durationMsOr("GEOPOLITICAL_FRONTEND_API_TIMEOUT_MS", 8000),
	})
	acledClient := acled.NewClient(acled.Config{
		BaseURL:           envOr("ACLED_BASE_URL", acled.DefaultBaseURL),
		APIToken:          envOr("ACLED_API_TOKEN", ""),
		Email:             envOr("ACLED_EMAIL", ""),
		AccessKey:         envOr("ACLED_ACCESS_KEY", ""),
		RequestTimeout:    durationMsOr("ACLED_HTTP_TIMEOUT_MS", 5000),
		MockEnabled:       boolOr("ACLED_MOCK_ENABLED", false),
		MockDataPath:      envOr("ACLED_MOCK_DATA_PATH", "data/mock/acled-events.json"),
		SnapshotStorePath: envOr("ACLED_SNAPSHOT_STATE_PATH", "data/providers/geopolitical/acled.json"),
	})
	if validationErr := validateACLEDMockRuntime(boolOr("ACLED_MOCK_ENABLED", false)); validationErr != nil {
		return nil, validationErr
	}
	gdeltGeoClient := gdelt.NewClient(gdelt.Config{
		BaseURL:        envOr("GDELT_BASE_URL", gdelt.DefaultBaseURL),
		RequestTimeout: durationMsOr("GDELT_HTTP_TIMEOUT_MS", 5000),
		RequestRetries: intOr("GDELT_HTTP_RETRIES", intOr("NEWS_HTTP_RETRIES", 1)),
	})
	var muxRouterSnapshotter *adaptive.Router
	quoteClient := marketServices.NewQuoteClient(gctClient, finnhubClient, macroClient, ecbClient)
	macroService := marketServices.NewMacroService(macroClient, ecbClient)
	depthClient := marketServices.NewDepthClient(gctClient)
	streamClient := marketServices.NewStreamClient(quoteClient, gctClient, finnhubClient)
	if connectorRegistry != nil {
		adaptiveRouter := adaptive.NewFromRegistry(connectorRegistry)
		quoteClient.SetAdaptiveRouter(adaptiveRouter)
		macroService.SetAdaptiveRouter(adaptiveRouter)
		depthClient.SetAdaptiveRouter(adaptiveRouter)
		streamClient.SetAdaptiveRouter(adaptiveRouter)
		muxRouterSnapshotter = adaptiveRouter
	}
	geopoliticalEventsService := geopoliticalServices.NewEventsService(acledClient, gdeltGeoClient)
	cfrClient := cfr.NewClient()
	crisiswatchClient := crisiswatch.NewClient(crisiswatch.Config{
		RSSURL:            envOr("CRISISWATCH_RSS_URL", crisiswatch.DefaultRSSURL),
		RequestTimeout:    durationMsOr("CRISISWATCH_HTTP_TIMEOUT_MS", 5000),
		CacheTTL:          durationMsOr("CRISISWATCH_CACHE_TTL_MS", 300000),
		PersistPath:       envOr("CRISISWATCH_CACHE_PERSIST_PATH", ""),
		SnapshotStorePath: envOr("CRISISWATCH_SNAPSHOT_STATE_PATH", "data/providers/geopolitical/crisiswatch.json"),
	})
	geopoliticalContextService := geopoliticalServices.NewContextService(cfrClient, crisiswatchClient)
	gameTheoryClient := gametheory.NewClient(gametheory.Config{
		BaseURL:        envOr("GEOPOLITICAL_GAMETHEORY_URL", gametheory.DefaultBaseURL),
		RequestTimeout: durationMsOr("GEOPOLITICAL_GAMETHEORY_TIMEOUT_MS", 5000),
	})
	memCache := cache.NewAdapterFromEnv()

	// NATS Publisher (P3.1–P3.7) — opt-in via NATS_ENABLED=true
	var natsPub messaging.Publisher = messaging.NoopPublisher{}
	if boolOr("NATS_ENABLED", false) {
		natsURL := envOr("NATS_URL", "nats://127.0.0.1:4222")
		if np, publishErr := messaging.NewNATSPublisher(natsURL); publishErr != nil {
			slog.Warn("[wiring] NATS unavailable, noop", "error", publishErr)
		} else {
			natsPub = np
			slog.Info("[wiring] NATS connected", "url", natsURL)
		}
	}

	memoryClient := memory.NewClient(memory.Config{
		BaseURL:        envOr("MEMORY_SERVICE_URL", memory.DefaultBaseURL),
		RequestTimeout: durationMsOr("MEMORY_SERVICE_TIMEOUT_MS", 5000),
		Registry:       connectorRegistry,
	})
	agentServiceClient := agentservice.NewClient(agentservice.Config{
		BaseURL:        envOr("AGENT_SERVICE_URL", agentservice.DefaultBaseURL),
		RequestTimeout: durationMsOr("AGENT_SERVICE_TIMEOUT_MS", 5000),
		Registry:       connectorRegistry,
	})
	capRegistry := capability.NewRegistry()
	if capPath := envOr("CAPABILITY_REGISTRY_PATH", "config/capabilities.yaml"); capPath != "" {
		if loadErr := capRegistry.LoadFromFile(capPath); loadErr != nil {
			slog.Warn("[wiring] capability registry load failed", "path", capPath, "error", loadErr)
		}
	}
	geopoliticalGameTheoryService := geopoliticalServices.NewGameTheoryService(acledClient, gameTheoryClient)
	geopoliticalCandidateReviewStore := geopoliticalServices.NewCandidateReviewStore(
		envOr("GEOPOLITICAL_CANDIDATE_QUEUE_STORE_PATH", "data/geopolitical/gateway-candidates.json"),
	)
	geopoliticalContradictionsStore := geopoliticalServices.NewContradictionsStore(
		envOr("GEOPOLITICAL_CONTRADICTIONS_STORE_PATH", "data/geopolitical/gateway-contradictions.json"),
	)
	geopoliticalTimelineStore := geopoliticalServices.NewTimelineStore(
		envOr("GEOPOLITICAL_TIMELINE_STORE_PATH", "data/geopolitical/gateway-timeline.json"),
	)
	geopoliticalEventsStore := geopoliticalServices.NewEventsStore(
		envOr("GEOPOLITICAL_EVENTS_STORE_PATH", "data/geopolitical/gateway-events.json"),
	)
	geopoliticalIngestRunsStore := geopoliticalServices.NewIngestRunsStore(
		envOr("GEOPOLITICAL_INGEST_RUNS_STORE_PATH", "data/geopolitical/gateway-ingest-runs.json"),
	)
	geopoliticalIngestShadowCompareEnabled := boolOr("GEOPOLITICAL_INGEST_SHADOW_COMPARE", true)
	geopoliticalGeoMapSourcePack := geomapsources.NewGeoMapSourcePack(geomapsources.PackConfig{
		DataDir: envOr("GEOPOLITICAL_DATA_DIR", "data"),
	})
	geopoliticalIngestHardMode := geopoliticalIngestModeOr("GEOPOLITICAL_INGEST_HARD_MODE", "go-owned-gateway-v1")
	geopoliticalIngestSoftMode := geopoliticalIngestModeOr("GEOPOLITICAL_INGEST_SOFT_MODE", "go-owned-gateway-v1")
	geopoliticalAdminSeedMode := geopoliticalAdminSeedModeOr("GEOPOLITICAL_ADMIN_SEED_MODE", "go-owned-gateway-v1")
	rssClient := newsConnectors.NewRSSClient(newsConnectors.RSSClientConfig{
		FeedURLs:       csvOr("NEWS_RSS_FEEDS", []string{"https://feeds.marketwatch.com/marketwatch/topstories/"}),
		RequestTimeout: durationMsOr("NEWS_HTTP_TIMEOUT_MS", 4000),
		RequestRetries: intOr("NEWS_HTTP_RETRIES", 1),
	})
	gdeltClient := newsConnectors.NewGDELTClient(newsConnectors.GDELTClientConfig{
		BaseURL:           envOr("GDELT_BASE_URL", newsConnectors.DefaultGDELTBaseURL),
		RequestTimeout:    durationMsOr("NEWS_HTTP_TIMEOUT_MS", 4000),
		RequestRetries:    intOr("NEWS_HTTP_RETRIES", 1),
		SnapshotStorePath: envOr("GDELT_NEWS_SNAPSHOT_STATE_PATH", "data/providers/news/gdelt-news.json"),
	})
	finvizClient := newsConnectors.NewFinvizClient(newsConnectors.FinvizClientConfig{
		BaseURL:        envOr("FINVIZ_RSS_BASE_URL", newsConnectors.DefaultFinvizBaseURL),
		RequestTimeout: durationMsOr("NEWS_HTTP_TIMEOUT_MS", 4000),
		RequestRetries: intOr("NEWS_HTTP_RETRIES", 1),
	})
	newsService := marketServices.NewNewsService(rssClient, gdeltClient, finvizClient)
	if muxRouterSnapshotter != nil {
		newsService.SetAdaptiveRouter(muxRouterSnapshotter)
	}
	strategyExamplesDir := envOr("GCT_STRATEGY_EXAMPLES_DIR", "go-crypto-trader/backtester/config/strategyexamples")
	backtestExecutor := backtestServices.Executor(backtestServices.NewSimulatedExecutor())
	if boolOr("GCT_BACKTEST_EXECUTOR_ENABLED", false) {
		gctBacktestExecutor, executorErr := backtestServices.NewGCTExecutor(backtestServices.GCTExecutorConfig{
			Address:               envOr("GCT_BACKTEST_GRPC_ADDRESS", ""),
			Username:              gctBacktestUsername,
			Password:              gctBacktestPassword,
			InsecureSkipVerifyTLS: boolOr("GCT_BACKTEST_INSECURE_TLS", false),
			RequestTimeout:        durationMsOr("GCT_BACKTEST_REQUEST_TIMEOUT_MS", 8000),
			PollInterval:          durationMsOr("GCT_BACKTEST_POLL_INTERVAL_MS", 750),
			ReportOutputDir:       envOr("GCT_BACKTEST_REPORT_OUTPUT_DIR", "go-crypto-trader/backtester/results"),
		})
		if executorErr != nil {
			return nil, fmt.Errorf("init gct backtest executor: %w", executorErr)
		}
		backtestExecutor = gctBacktestExecutor
	}
	backtestManager := backtestServices.NewManagerWithExecutor(
		strategyExamplesDir,
		backtestExecutor,
		durationMsOr("GCT_BACKTEST_RUN_TIMEOUT_MS", 300000),
	)
	jwtRevocations := newJWTRevocationBlocklist()
	jwtRevocationAudit := httpHandlers.NewJWTRevocationAuditStore(intOr("AUTH_JWT_REVOCATION_AUDIT_CAPACITY", 200))
	jwtRevocationAuditJSONL := auditjsonl.NewHashChainLogger(jwtRevocationAuditJSONLPathFromEnv())
	jwtRevocationAuditEnabled := boolOr("AUTH_JWT_REVOCATION_AUDIT_JSONL_ENABLED", true)
	var jwtRevocationAuditDB *httpHandlers.JWTRevocationAuditSQLiteStore
	if boolOr("AUTH_JWT_REVOCATION_AUDIT_DB_ENABLED", false) {
		store, auditDBErr := httpHandlers.NewJWTRevocationAuditSQLiteStore(jwtRevocationAuditSQLitePathFromEnv())
		if auditDBErr != nil {
			return nil, fmt.Errorf("init jwt revocation audit db: %w", auditDBErr)
		}
		jwtRevocationAuditDB = store
	}
	for _, revokedJTI := range csvOr("AUTH_JWT_REVOKED_JTIS", nil) {
		if strings.TrimSpace(revokedJTI) == "" {
			continue
		}
		jwtRevocations.Revoke(revokedJTI, time.Now().Add(durationMsOr("AUTH_JWT_BLOCKLIST_DEFAULT_TTL_MS", 15*60*1000)))
	}

	// GCT Audit: SQLite primary (default true when GCT_AUDIT_ENABLED), JSONL as fallback/degraded
	var gctAuditDB *httpHandlers.GCTAuditSQLiteStore
	if boolOr("GCT_AUDIT_DB_ENABLED", true) {
		store, auditErr := httpHandlers.NewGCTAuditSQLiteStore(gctAuditSQLitePathFromEnv())
		if auditErr != nil {
			// Degraded: log and continue with JSONL only (no fail-fast for audit DB)
			slog.Warn("[gct-audit] SQLite init failed, using JSONL only", "error", auditErr)
		} else {
			gctAuditDB = store
		}
	}

	artifactMetadataProvider := envOr("ARTIFACT_STORAGE_METADATA_PROVIDER", "")
	if artifactMetadataProvider == "" && boolOr("POSTGRES_ENABLED", false) {
		artifactMetadataProvider = "postgres"
	}
	artifactStore, err := storage.NewArtifactMetadataStore(
		artifactMetadataProvider,
		envOr("ARTIFACT_STORAGE_METADATA_DB_PATH", "data/storage/artifacts.db"),
		envOr("POSTGRES_DSN", ""),
	)
	if err != nil {
		return nil, fmt.Errorf("init artifact metadata store: %w", err)
	}
	artifactService, err := storage.NewService(storage.Config{
		Provider:      storage.ProviderKind(envOr("ARTIFACT_STORAGE_PROVIDER", string(storage.ProviderFilesystem))),
		BaseDir:       envOr("ARTIFACT_STORAGE_BASE_DIR", "data/storage/objects"),
		SigningSecret: artifactSigningSecretFromEnv(),
		TTL:           durationMsOr("ARTIFACT_STORAGE_SIGNED_URL_TTL_MS", 15*60*1000),
		Store:         artifactStore,
		S3: storage.S3Config{
			Endpoint:        envOr("ARTIFACT_STORAGE_S3_ENDPOINT", ""),
			Region:          envOr("ARTIFACT_STORAGE_S3_REGION", "us-east-1"),
			Bucket:          envOr("ARTIFACT_STORAGE_S3_BUCKET", ""),
			AccessKeyID:     envOr("ARTIFACT_STORAGE_S3_ACCESS_KEY_ID", ""),
			SecretAccessKey: envOr("ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY", ""),
			UsePathStyle:    boolOr("ARTIFACT_STORAGE_S3_USE_PATH_STYLE", true),
			CreateBucket:    boolOr("ARTIFACT_STORAGE_S3_CREATE_BUCKET", true),
		},
	})
	if err != nil {
		_ = artifactStore.Close()
		return nil, fmt.Errorf("init artifact storage service: %w", err)
	}
	artifactGatewayBaseURL := artifactGatewayBaseURLFromEnv(host, port)
	appStateStore, err := appstate.NewSQLiteStore(backendAppDBPathFromEnv())
	if err != nil {
		_ = artifactStore.Close()
		return nil, fmt.Errorf("init app state store: %w", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", httpHandlers.HealthHandler(gctClient))
	mux.HandleFunc("/api/v1/gct/health", httpHandlers.HealthHandler(gctClient))
	mux.HandleFunc("/api/v1/storage/artifacts/upload-url", httpHandlers.ArtifactUploadURLHandler(artifactService, artifactGatewayBaseURL))
	mux.HandleFunc("/api/v1/storage/artifacts/upload/", httpHandlers.ArtifactUploadHandler(artifactService))
	mux.HandleFunc("/api/v1/storage/artifacts/", httpHandlers.ArtifactMetadataHandler(artifactService))
	mux.HandleFunc("/api/v1/fusion/preferences", httpHandlers.FusionPreferencesHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/orders", httpHandlers.FusionOrdersHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/orders/", httpHandlers.FusionOrderDetailHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/alerts", httpHandlers.FusionAlertsHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/alerts/", httpHandlers.FusionAlertDetailHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/trade-journal", httpHandlers.FusionTradeJournalHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/trade-journal/", httpHandlers.FusionTradeJournalDetailHandler(appStateStore))
	mux.HandleFunc("/api/v1/fusion/portfolio/history", httpHandlers.FusionPortfolioHistoryHandler(appStateStore))
	mux.HandleFunc("/api/v1/files/audit", httpHandlers.FileAuditLogHandler(appStateStore))
	mux.HandleFunc("/api/v1/control/audit", httpHandlers.ControlAuditLogHandler(appStateStore))
	mux.HandleFunc("/api/v1/admin/users", httpHandlers.AdminUsersHandler(appStateStore))
	mux.HandleFunc("/api/v1/auth/current-user", httpHandlers.CurrentUserHandler(appStateStore))
	mux.HandleFunc("/api/v1/auth/consent", httpHandlers.AuthConsentHandler(appStateStore))
	mux.HandleFunc("/api/v1/auth/actions/", httpHandlers.AuthActionsHandler(appStateStore))
	mux.HandleFunc("/api/v1/auth/owner/", httpHandlers.AuthOwnerHandler(appStateStore))
	mux.HandleFunc("/api/v1/auth/passkeys/", httpHandlers.AuthPasskeysHandler(appStateStore))
	if muxRouterSnapshotter != nil {
		mux.HandleFunc("/api/v1/router/providers", httpHandlers.RouterProvidersHandler(muxRouterSnapshotter))
	}
	mux.HandleFunc("/api/v1/quote", httpHandlers.QuoteHandler(quoteClient))
	mux.HandleFunc("/api/v1/orderbook", httpHandlers.OrderbookHandler(depthClient))
	mux.HandleFunc("/api/v1/quote/fallback", httpHandlers.FinanceBridgeQuoteFallbackHandler(yahooClient))
	mux.HandleFunc(
		"/api/v1/auth/revocations/jti",
		httpHandlers.JWTJTIRevocationHandlerWithAudit(jwtRevocations.Revoke, func(record httpHandlers.JWTRevocationAuditRecord) {
			jwtRevocationAudit.Append(record)
			if jwtRevocationAuditDB != nil {
				_ = jwtRevocationAuditDB.Append(record)
			}
			if !jwtRevocationAuditEnabled || jwtRevocationAuditJSONL == nil {
				return
			}
			payload := map[string]any{
				"ts":         record.RecordedAt.UTC().Format(time.RFC3339Nano),
				"jti":        record.JTI,
				"requestId":  record.RequestID,
				"actorUser":  record.ActorUser,
				"actorRole":  record.ActorRole,
				"sourceIp":   record.SourceIP,
				"kind":       "jwt_revocation",
				"auditScope": "auth",
			}
			if !record.ExpiresAt.IsZero() {
				payload["expiresAt"] = record.ExpiresAt.UTC().Format(time.RFC3339)
			}
			_ = jwtRevocationAuditJSONL.Append(payload)
		}),
	)
	mux.HandleFunc(
		"/api/v1/auth/revocations/user",
		httpHandlers.JWTUserRevocationHandlerWithAudit(jwtRevocations.RevokeUser, func(record httpHandlers.JWTRevocationAuditRecord) {
			jwtRevocationAudit.Append(record)
			if jwtRevocationAuditDB != nil {
				_ = jwtRevocationAuditDB.Append(record)
			}
			if !jwtRevocationAuditEnabled || jwtRevocationAuditJSONL == nil {
				return
			}
			payload := map[string]any{
				"ts":            record.RecordedAt.UTC().Format(time.RFC3339Nano),
				"userId":        strings.TrimPrefix(record.JTI, "GLOBAL_USER_REVOCATION:"),
				"revokedBefore": record.ExpiresAt.UTC().Format(time.RFC3339),
				"requestId":     record.RequestID,
				"actorUser":     record.ActorUser,
				"actorRole":     record.ActorRole,
				"sourceIp":      record.SourceIP,
				"kind":          "user_revocation",
				"auditScope":    "auth",
			}
			_ = jwtRevocationAuditJSONL.Append(payload)
		}),
	)
	jwtRevocationAuditLister := jwtRevocationAudit.List
	if jwtRevocationAuditDB != nil {
		jwtRevocationAuditLister = func(limit int) []httpHandlers.JWTRevocationAuditRecord {
			records, err := jwtRevocationAuditDB.List(limit)
			if err != nil {
				return jwtRevocationAudit.List(limit)
			}
			return records
		}
	}
	mux.HandleFunc("/api/v1/auth/revocations/audit", httpHandlers.JWTJTIRevocationAuditHandler(jwtRevocationAuditLister))
	mux.HandleFunc("/api/v1/ohlcv", httpHandlers.OHLCVHandler(yahooClient))
	mux.HandleFunc("/api/v1/search", httpHandlers.SearchHandler(symbolCatalogClient))
	mux.HandleFunc("/api/v1/macro/history", httpHandlers.MacroHistoryHandler(macroService))
	mux.HandleFunc("/api/v1/stream/market", sseHandlers.MarketStreamHandler(streamClient, natsPub))
	mux.HandleFunc("/api/v1/stream/orderbook", sseHandlers.OrderbookStreamHandler(depthClient))
	mux.HandleFunc("/api/v1/news/headlines", httpHandlers.NewsHandler(newsService))
	mux.HandleFunc("/api/v1/signals/composite", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/signals/composite"))
	mux.HandleFunc("/api/v1/evaluate/strategy", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/evaluate/strategy"))
	mux.HandleFunc("/api/v1/cluster-headlines", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/cluster-headlines"))
	mux.HandleFunc("/api/v1/social-surge", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/social-surge"))
	mux.HandleFunc("/api/v1/narrative-shift", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/narrative-shift"))
	mux.HandleFunc("/api/v1/ingest/classify", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/ingest/classify"))
	mux.HandleFunc("/api/v1/geopolitical/events", httpHandlers.GeopoliticalEventsHandler(geopoliticalEventsService))
	mux.HandleFunc("/api/v1/geopolitical/local-events", httpHandlers.GeopoliticalLocalEventsHandler(geopoliticalEventsStore))
	mux.HandleFunc("/api/v1/geopolitical/local-events/", httpHandlers.GeopoliticalLocalEventsHandler(geopoliticalEventsStore))
	mux.HandleFunc("/api/v1/geopolitical/context", httpHandlers.GeopoliticalContextHandler(geopoliticalContextService))
	mux.HandleFunc("/api/v1/geopolitical/candidates", httpHandlers.GeopoliticalCandidatesProxyHandler(geopoliticalNextClient, geopoliticalCandidateReviewStore, geopoliticalTimelineStore, geopoliticalEventsStore))
	mux.HandleFunc("/api/v1/geopolitical/candidates/", httpHandlers.GeopoliticalCandidatesProxyHandler(geopoliticalNextClient, geopoliticalCandidateReviewStore, geopoliticalTimelineStore, geopoliticalEventsStore))
	mux.HandleFunc("/api/v1/geopolitical/contradictions", httpHandlers.GeopoliticalContradictionsHandler(geopoliticalContradictionsStore, geopoliticalTimelineStore))
	mux.HandleFunc("/api/v1/geopolitical/contradictions/", httpHandlers.GeopoliticalContradictionsHandler(geopoliticalContradictionsStore, geopoliticalTimelineStore))
	mux.HandleFunc("/api/v1/geopolitical/timeline", httpHandlers.GeopoliticalTimelineHandler(geopoliticalTimelineStore))
	mux.HandleFunc("/api/v1/geopolitical/ingest/runs", httpHandlers.GeopoliticalIngestRunsHandler(geopoliticalIngestRunsStore))
	mux.HandleFunc("/api/v1/geopolitical/migration/status", httpHandlers.GeopoliticalMigrationStatusHandler(httpHandlers.GeopoliticalMigrationStatusConfig{
		CandidatesListMode:        "go-owned",
		CandidateRejectSnoozeMode: "go-owned",
		CandidateAcceptMode:       "go-owned",
		ContradictionsMode:        "go-owned",
		TimelineMode:              "go-owned",
		IngestHardMode:            geopoliticalIngestHardMode,
		IngestSoftMode:            geopoliticalIngestSoftMode,
		AdminSeedMode:             geopoliticalAdminSeedMode,
		IngestShadowCompare:       geopoliticalIngestShadowCompareEnabled,
		CandidatesStore:           geopoliticalCandidateReviewStore,
		ContradictionsStore:       geopoliticalContradictionsStore,
		TimelineStore:             geopoliticalTimelineStore,
		IngestRunsStore:           geopoliticalIngestRunsStore,
	}))
	geopoliticalHardIngestHandler := httpHandlers.GeopoliticalHardIngestHandler(geopoliticalEventsService, geopoliticalCandidateReviewStore, geopoliticalIngestRunsStore)
	if geopoliticalIngestHardMode == "next-proxy" {
		geopoliticalHardIngestHandler = httpHandlers.GeopoliticalIngestAdminProxyHandler(geopoliticalNextClient, "/api/geopolitical/candidates/ingest/hard", geopoliticalCandidateReviewStore, nil, nil, geopoliticalIngestRunsStore, geopoliticalIngestShadowCompareEnabled)
	}
	mux.HandleFunc(
		"/api/v1/geopolitical/ingest/hard",
		geopoliticalHardIngestHandler,
	)
	geopoliticalSoftIngestHandler := httpHandlers.GeopoliticalSoftIngestHandler(newsService, softSignalsProxyClient, geopoliticalCandidateReviewStore, geopoliticalIngestRunsStore)
	if geopoliticalIngestSoftMode == "next-proxy" {
		geopoliticalSoftIngestHandler = httpHandlers.GeopoliticalIngestAdminProxyHandler(geopoliticalNextClient, "/api/geopolitical/candidates/ingest/soft", geopoliticalCandidateReviewStore, nil, nil, geopoliticalIngestRunsStore, geopoliticalIngestShadowCompareEnabled)
	}
	mux.HandleFunc(
		"/api/v1/geopolitical/ingest/soft",
		geopoliticalSoftIngestHandler,
	)
	geopoliticalAdminSeedHandler := httpHandlers.GeopoliticalIngestAdminProxyHandler(geopoliticalNextClient, "/api/geopolitical/seed", geopoliticalCandidateReviewStore, geopoliticalContradictionsStore, geopoliticalTimelineStore, geopoliticalIngestRunsStore, false)
	if geopoliticalAdminSeedMode == "go-owned-gateway-v1" {
		geopoliticalAdminSeedHandler = httpHandlers.GeopoliticalSeedHandler(
			geopoliticalCandidateReviewStore,
			geopoliticalContradictionsStore,
			geopoliticalTimelineStore,
			geopoliticalEventsStore,
			geopoliticalIngestRunsStore,
		)
	}
	mux.HandleFunc(
		"/api/v1/geopolitical/admin/seed",
		geopoliticalAdminSeedHandler,
	)
	mux.HandleFunc(
		"/api/v1/geopolitical/admin/sanctions-fetch",
		httpHandlers.GeopoliticalSanctionsFetchHandler(geopoliticalGeoMapSourcePack, geopoliticalCandidateReviewStore),
	)
	mux.HandleFunc(
		"/api/v1/geopolitical/game-theory/impact",
		httpHandlers.GeopoliticalGameTheoryImpactHandler(geopoliticalGameTheoryService),
	)
	mux.HandleFunc("/api/v1/game-theory/nash-solve", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/game-theory/nash-solve"))
	mux.HandleFunc("/api/v1/game-theory/transmission-paths", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/game-theory/transmission-paths"))
	mux.HandleFunc("/api/v1/game-theory/monte-carlo", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/game-theory/monte-carlo"))
	mux.HandleFunc("/api/v1/game-theory/strategeme-match", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/game-theory/strategeme-match"))
	mux.HandleFunc("/api/v1/game-theory/timeline-regimes", httpHandlers.IndicatorProxyHandler(softSignalsProxyClient, "/api/v1/game-theory/timeline-regimes"))
	mux.HandleFunc("/api/v1/backtest/capabilities", httpHandlers.BacktestCapabilitiesHandler(strategyExamplesDir))
	mux.HandleFunc("/api/v1/backtest/runs", httpHandlers.BacktestRunsHandler(backtestManager))
	mux.HandleFunc("/api/v1/backtest/runs/", httpHandlers.BacktestRunByIDHandler(backtestManager))

	// Phase 6: Memory Architecture
	mux.HandleFunc("/api/v1/memory/kg/seed", httpHandlers.MemoryKGSeedHandler(memoryClient, memCache))
	mux.HandleFunc("/api/v1/memory/kg/query", httpHandlers.MemoryKGQueryHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/kg/nodes", httpHandlers.MemoryKGNodesHandler(memoryClient, memCache))
	mux.HandleFunc("/api/v1/memory/kg/sync", httpHandlers.MemoryKGSyncHandler(memoryClient, memCache))
	mux.HandleFunc("/api/v1/memory/episode", httpHandlers.MemoryEpisodePostHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/episodes", httpHandlers.MemoryEpisodesGetHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/search", httpHandlers.MemorySearchHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/health", httpHandlers.MemoryHealthHandler(memoryClient, memCache))
	// Phase 10e + 23: Agent WebMCP Tools via Go Policy Gateway (with Capability Registry)
	agentChartHandler := capability.CheckMiddleware(capRegistry, "tool.get_chart_state")(httpHandlers.AgentToolProxyHandler(agentServiceClient, "/api/v1/agent/tools/chart-state"))
	agentPortfolioHandler := capability.CheckMiddleware(capRegistry, "tool.get_portfolio_summary")(httpHandlers.AgentToolProxyHandler(agentServiceClient, "/api/v1/agent/tools/portfolio-summary"))
	agentGeomapHandler := capability.CheckMiddleware(capRegistry, "tool.get_geomap_focus")(httpHandlers.AgentToolProxyHandler(agentServiceClient, "/api/v1/agent/tools/geomap-focus"))
	mux.Handle("/api/v1/agent/tools/chart-state", agentChartHandler)
	mux.Handle("/api/v1/agent/tools/portfolio-summary", agentPortfolioHandler)
	mux.Handle("/api/v1/agent/tools/geomap-focus", agentGeomapHandler)
	// Phase 10.v3: Mutation tool — POST only, requires confirm in frontend
	agentSetChartHandler := capability.CheckMiddleware(capRegistry, "tool.set_chart_state")(httpHandlers.AgentMutationProxyHandler(agentServiceClient, "/api/v1/agent/tools/set_chart_state"))
	mux.Handle("/api/v1/agent/tools/set_chart_state", agentSetChartHandler)
	// Phase 22d: Agent Chat SSE proxy — Vercel AI Data Stream Protocol (AC6/AC79)
	mux.HandleFunc("/api/v1/agent/chat", httpHandlers.AgentChatHandler(envOr("AGENT_SERVICE_URL", agentservice.DefaultBaseURL)))
	// Phase 22f/ACR-G6: Tool Approval endpoint
	mux.HandleFunc("/api/v1/agent/approve", httpHandlers.AgentApproveHandler())

	// Phase 22f: Audio STT + TTS proxy (ACR-A2, ACR-A6)
	agentAudioBaseURL := envOr("AGENT_SERVICE_URL", agentservice.DefaultBaseURL)
	mux.HandleFunc("/api/v1/audio/transcribe", httpHandlers.AgentAudioTranscribeHandler(agentAudioBaseURL))
	mux.HandleFunc("/api/v1/audio/synthesize", httpHandlers.AgentAudioSynthesizeHandler(agentAudioBaseURL))

	// Phase 5a: GCT Portfolio Bridge
	gctPortfolioHandler := httpHandlers.GCTPortfolioHandler(gctClient)
	mux.HandleFunc("/api/v1/gct/portfolio/summary", gctPortfolioHandler)
	mux.HandleFunc("/api/v1/gct/portfolio/positions", gctPortfolioHandler)
	mux.HandleFunc("/api/v1/gct/portfolio/balances/", gctPortfolioHandler)
	mux.HandleFunc("/api/v1/gct/exchanges", gctPortfolioHandler)

	// Phase 5b: Portfolio Analytics (proxy → Python indicator-service)
	mux.HandleFunc("/api/v1/portfolio/correlations", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/correlations"))
	mux.HandleFunc("/api/v1/portfolio/rolling-metrics", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/rolling-metrics"))
	mux.HandleFunc("/api/v1/portfolio/drawdown-analysis", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/drawdown-analysis"))
	mux.HandleFunc("/api/v1/portfolio/optimize", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/optimize"))

	// Phase 13: Advanced Portfolio Analytics
	mux.HandleFunc("/api/v1/portfolio/kelly-allocation", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/kelly-allocation"))
	mux.HandleFunc("/api/v1/portfolio/regime-sizing", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/regime-sizing"))
	mux.HandleFunc("/api/v1/portfolio/monte-carlo-var", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/monte-carlo-var"))
	mux.HandleFunc("/api/v1/portfolio/risk-warning", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/portfolio/risk-warning"))

	// Phase 7b: Indicator Catalog — proxy all un-wired Python endpoints
	mux.HandleFunc("/api/v1/indicators/swings", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/swings"))
	mux.HandleFunc("/api/v1/indicators/exotic-ma", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/exotic-ma"))
	mux.HandleFunc("/api/v1/indicators/ks-collection", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/ks-collection"))
	mux.HandleFunc("/api/v1/indicators/ichimoku", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/ichimoku"))
	mux.HandleFunc("/api/v1/indicators/macd", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/macd"))
	mux.HandleFunc("/api/v1/indicators/stochastic", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/stochastic"))
	mux.HandleFunc("/api/v1/indicators/adx", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/adx"))
	mux.HandleFunc("/api/v1/indicators/hma", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/hma"))
	mux.HandleFunc("/api/v1/indicators/vwap", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/vwap"))
	mux.HandleFunc("/api/v1/indicators/keltner", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/keltner"))
	mux.HandleFunc("/api/v1/patterns/candlestick", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/patterns/candlestick"))
	mux.HandleFunc("/api/v1/patterns/harmonic", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/patterns/harmonic"))
	mux.HandleFunc("/api/v1/patterns/timing", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/patterns/timing"))
	mux.HandleFunc("/api/v1/patterns/price", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/patterns/price"))
	mux.HandleFunc("/api/v1/patterns/elliott-wave", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/patterns/elliott-wave"))
	mux.HandleFunc("/api/v1/fibonacci/levels", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/fibonacci/levels"))
	mux.HandleFunc("/api/v1/fibonacci/confluence", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/fibonacci/confluence"))
	mux.HandleFunc("/api/v1/charting/transform", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/charting/transform"))
	mux.HandleFunc("/api/v1/indicators/bollinger/bandwidth", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/bollinger/bandwidth"))
	mux.HandleFunc("/api/v1/indicators/bollinger/percent-b", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/bollinger/percent-b"))
	mux.HandleFunc("/api/v1/indicators/bollinger/squeeze", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/bollinger/squeeze"))
	mux.HandleFunc("/api/v1/indicators/rsi/atr-adjusted", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/rsi/atr-adjusted"))
	mux.HandleFunc("/api/v1/indicators/rsi/bollinger", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/rsi/bollinger"))

	// Phase 15b: Volatility Suite
	mux.HandleFunc("/api/v1/indicators/volatility-suite", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/volatility-suite"))

	// Phase 15c: Regime Detection
	mux.HandleFunc("/api/v1/regime/detect", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/regime/detect"))
	mux.HandleFunc("/api/v1/regime/markov", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/regime/markov"))
	mux.HandleFunc("/api/v1/regime/hmm", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/regime/hmm"))

	// Phase 15d-15h: Advanced indicators + eval baseline
	mux.HandleFunc("/api/v1/indicators/alternative-bars", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/alternative-bars"))
	mux.HandleFunc("/api/v1/indicators/cusum", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/indicators/cusum"))
	mux.HandleFunc("/api/v1/regime/meanrev-momentum", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/regime/meanrev-momentum"))
	mux.HandleFunc("/api/v1/eval/performance-metrics", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/eval/performance-metrics"))
	mux.HandleFunc("/api/v1/signals/quality-chain", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/signals/quality-chain"))
	mux.HandleFunc("/api/v1/orderflow/state-machine", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/orderflow/state-machine"))
	mux.HandleFunc("/api/v1/eval/baseline", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/eval/baseline"))

	// Phase 16: Backtesting + eval hardening
	mux.HandleFunc("/api/v1/backtest/run", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/backtest/run"))
	mux.HandleFunc("/api/v1/backtest/walk-forward", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/backtest/walk-forward"))
	mux.HandleFunc("/api/v1/backtest/triple-barrier", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/backtest/triple-barrier"))
	mux.HandleFunc("/api/v1/backtest/parameter-sensitivity", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/backtest/parameter-sensitivity"))
	mux.HandleFunc("/api/v1/eval/deflated-sharpe", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/eval/deflated-sharpe"))
	mux.HandleFunc("/api/v1/eval/indicator", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/eval/indicator"))

	// Phase 20: ML pipeline
	mux.HandleFunc("/api/v1/ml/feature-engineering", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/ml/feature-engineering"))
	mux.HandleFunc("/api/v1/ml/classify-signal", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/ml/classify-signal"))
	mux.HandleFunc("/api/v1/ml/hybrid-fusion", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/ml/hybrid-fusion"))
	mux.HandleFunc("/api/v1/ml/bias-monitoring", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/ml/bias-monitoring"))

	// Phase 18: Options + Dark Pool + DeFi + Oracle Cross-Check
	mux.HandleFunc("/api/v1/darkpool/signal", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/darkpool/signal"))
	mux.HandleFunc("/api/v1/options/gex-profile", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/options/gex-profile"))
	mux.HandleFunc("/api/v1/options/expected-move", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/options/expected-move"))
	mux.HandleFunc("/api/v1/options/calculator", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/options/calculator"))
	mux.HandleFunc("/api/v1/defi/stress", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/defi/stress"))
	mux.HandleFunc("/api/v1/oracle/cross-check", httpHandlers.IndicatorProxyHandler(indicatorServiceClient, "/api/v1/oracle/cross-check"))

	// FlightRecorder (P6c) — Go-runtime tracing, complements OTel distributed tracing.
	// go tool trace flight.trace to analyze goroutine/GC/scheduler data.
	if boolOr("FLIGHT_RECORDER_ENABLED", false) {
		fr := observability.NewFlightRecorder()
		if err := fr.Start(); err != nil {
			slog.Warn("[wiring] FlightRecorder start failed", "error", err)
		} else {
			mux.HandleFunc("/debug/flight-recorder", fr.HTTPHandler())
		}
	}

	if boolOr("MACRO_INGEST_ENABLED", false) {
		macroIngest := marketServices.NewMacroIngestService(
			macroService,
			envOr("MACRO_INGEST_OUTPUT_DIR", "data/macro"),
			durationMsOr("MACRO_INGEST_REQUEST_TIMEOUT_MS", 8000),
		)
		targets := macroTargetsOr(os.Getenv("MACRO_INGEST_TARGETS"), []marketServices.MacroIngestTarget{
			{Exchange: "FED", Symbol: "POLICY_RATE", Asset: "macro", Limit: 180},
			{Exchange: "ECB", Symbol: "EUR/USD", Asset: "forex", Limit: 180},
			{Exchange: "BOJ", Symbol: "POLICY_RATE", Asset: "macro", Limit: 180},
			{Exchange: "SNB", Symbol: "POLICY_RATE", Asset: "macro", Limit: 180},
			{Exchange: "BCB", Symbol: "POLICY_RATE", Asset: "macro", Limit: 180},
			{Exchange: "BCRA", Symbol: "POLICY_RATE", Asset: "macro", Limit: 180},
		})
		macroIngest.StartBackground(
			context.Background(),
			durationMsOr("MACRO_INGEST_INTERVAL_MS", 30*60*1000),
			targets,
		)
	}

	allowedOrigins := csvOr("CORS_ALLOWED_ORIGINS", []string{
		"http://127.0.0.1:3000",
		"http://localhost:3000",
	})
	authStackBypassEnabled := boolOr("AUTH_STACK_BYPASS", false) || boolOr("NEXT_PUBLIC_AUTH_STACK_BYPASS", false)
	if err := validateAuthBypassRuntime(authStackBypassEnabled); err != nil {
		return nil, err
	}
	authJWTEnabled := boolOr("AUTH_JWT_ENFORCE", false) && !authStackBypassEnabled
	authRBACEnabled := boolOr("AUTH_RBAC_ENFORCE", false) && !authStackBypassEnabled
	authRateLimitEnabled := boolOr("AUTH_RATE_LIMIT_ENFORCE", false) && !authStackBypassEnabled
	handler := withRequestIDAndLogging(
		withCORS(
			withSecurityHeaders(
				withRBAC(
					withJWTAuth(
						withGCTAudit(
							withRateLimit(mux, rateLimitConfig{
								enabled: authRateLimitEnabled,
							}),
							gctAuditConfig{
								enabled: boolOr("GCT_AUDIT_ENABLED", true),
								path:    gctAuditJSONLPathFromEnv(),
								onRecord: func(record map[string]any) {
									if gctAuditDB != nil {
										_ = gctAuditDB.Append(record)
									}
								},
							},
						),
						jwtAuthConfig{
							enabled: authJWTEnabled,
							secret: strings.TrimSpace(
								envOr("AUTH_JWT_SECRET", envOr("AUTH_SECRET", envOr("NEXTAUTH_SECRET", ""))),
							),
							issuer:      strings.TrimSpace(envOr("AUTH_JWT_ISSUER", "")),
							audience:    strings.TrimSpace(envOr("AUTH_JWT_AUDIENCE", "")),
							validAlgs:   csvOr("AUTH_JWT_ALLOWED_ALGS", []string{"HS256"}),
							leeway:      time.Duration(intOr("AUTH_JWT_LEEWAY_SEC", 0)) * time.Second,
							revocations: jwtRevocations,
						},
					),
					rbacConfig{
						enabled: authRBACEnabled,
					},
				),
			),
			allowedOrigins,
		),
	)
	if boolOr("OTEL_ENABLED", false) {
		handler = otelhttp.NewHandler(handler, "go-gateway")
	}
	server := NewServer(host, port, handler)
	server.closeFn = func() error {
		if err := appStateStore.Close(); err != nil {
			_ = artifactStore.Close()
			return fmt.Errorf("close app state store: %w", err)
		}
		if err := artifactStore.Close(); err != nil {
			return fmt.Errorf("close artifact metadata store: %w", err)
		}
		return nil
	}
	return server, nil
}

func envOr(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func intOr(key string, fallback int) int {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func durationMsOr(key string, fallbackMs int) time.Duration {
	value := intOr(key, fallbackMs)
	if value < 1 {
		value = fallbackMs
	}
	return time.Duration(value) * time.Millisecond
}

func boolOr(key string, fallback bool) bool {
	value := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
	if value == "" {
		return fallback
	}

	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func csvOr(key string, fallback []string) []string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}

	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	if len(result) == 0 {
		return fallback
	}
	return result
}

func geopoliticalIngestModeOr(key, fallback string) string {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	switch value {
	case "":
		return fallback
	case "next-proxy", "go-owned-gateway-v1":
		return value
	default:
		return fallback
	}
}

func geopoliticalAdminSeedModeOr(key, fallback string) string {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	switch value {
	case "":
		return fallback
	case "next-proxy+go-sync", "go-owned-gateway-v1":
		return value
	default:
		return fallback
	}
}

func macroTargetsOr(value string, fallback []marketServices.MacroIngestTarget) []marketServices.MacroIngestTarget {
	raw := strings.TrimSpace(value)
	if raw == "" {
		return fallback
	}

	items := strings.Split(raw, ";")
	targets := make([]marketServices.MacroIngestTarget, 0, len(items))
	for _, item := range items {
		part := strings.TrimSpace(item)
		if part == "" {
			continue
		}
		fields := strings.Split(part, "|")
		if len(fields) < 3 {
			continue
		}
		target := marketServices.MacroIngestTarget{
			Exchange: strings.ToUpper(strings.TrimSpace(fields[0])),
			Symbol:   strings.TrimSpace(fields[1]),
			Asset:    strings.ToLower(strings.TrimSpace(fields[2])),
			Limit:    180,
		}
		if len(fields) >= 4 {
			if parsed, err := strconv.Atoi(strings.TrimSpace(fields[3])); err == nil && parsed > 0 {
				target.Limit = parsed
			}
		}
		if target.Exchange == "" || target.Symbol == "" || target.Asset == "" {
			continue
		}
		targets = append(targets, target)
	}
	if len(targets) == 0 {
		return fallback
	}
	return targets
}

func loadConnectorRegistry() (*connectorregistry.Registry, error) {
	paths := []string{
		strings.TrimSpace(os.Getenv("ADAPTIVE_ROUTER_CONFIG_PATH")),
		"config/provider-router.yaml",
		"go-backend/config/provider-router.yaml",
	}
	for _, path := range paths {
		if path == "" {
			continue
		}
		registry, err := connectorregistry.LoadFromFile(path)
		if err == nil {
			return registry, nil
		}
		if os.IsNotExist(err) {
			continue
		}
		return nil, fmt.Errorf("load connector registry from %s: %w", path, err)
	}
	return nil, nil
}

func validateAuthBypassRuntime(enabled bool) error {
	if !enabled {
		return nil
	}
	if !isProductionRuntime() {
		return nil
	}
	if boolOr("ALLOW_PROD_AUTH_STACK_BYPASS", false) {
		return nil
	}
	return fmt.Errorf("auth stack bypass must remain disabled in production (set ALLOW_PROD_AUTH_STACK_BYPASS=true only for explicit emergency override)")
}

func validateACLEDMockRuntime(enabled bool) error {
	if !enabled {
		return nil
	}
	if !isProductionRuntime() {
		return nil
	}
	if boolOr("ALLOW_PROD_ACLED_MOCK", false) {
		return nil
	}
	return fmt.Errorf("ACLED mock must remain disabled in production (set ALLOW_PROD_ACLED_MOCK=true only for explicit emergency override)")
}

func isProductionRuntime() bool {
	for _, key := range []string{"APP_ENV", "ENVIRONMENT", "GO_ENV", "NODE_ENV"} {
		value := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
		if value == "" {
			continue
		}
		if value == "prod" || value == "production" {
			return true
		}
	}
	return false
}

func artifactGatewayBaseURLFromEnv(host, port string) string {
	if configured := strings.TrimSpace(envOr("ARTIFACT_STORAGE_PUBLIC_BASE_URL", "")); configured != "" {
		return strings.TrimRight(configured, "/")
	}
	resolvedHost := strings.TrimSpace(host)
	if resolvedHost == "" || resolvedHost == "0.0.0.0" {
		resolvedHost = "127.0.0.1"
	}
	return fmt.Sprintf("http://%s:%s", resolvedHost, strings.TrimSpace(port))
}

func artifactSigningSecretFromEnv() string {
	candidates := []string{
		strings.TrimSpace(envOr("ARTIFACT_STORAGE_SIGNING_SECRET", "")),
		strings.TrimSpace(envOr("AUTH_JWT_SECRET", "")),
		strings.TrimSpace(envOr("AUTH_SECRET", "")),
		strings.TrimSpace(envOr("NEXTAUTH_SECRET", "")),
	}
	for _, candidate := range candidates {
		if candidate != "" {
			return candidate
		}
	}
	if !isProductionRuntime() {
		return "local-dev-artifact-signing-secret"
	}
	return ""
}

func backendAppDBPathFromEnv() string {
	if configured := strings.TrimSpace(envOr("BACKEND_APP_DB_PATH", "")); configured != "" {
		return configured
	}
	if configured := strings.TrimSpace(envOr("ARTIFACT_STORAGE_METADATA_DB_PATH", "")); configured != "" {
		return configured
	}
	return "data/backend.db"
}
