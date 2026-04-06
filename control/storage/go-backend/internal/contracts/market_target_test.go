package contracts

import "testing"

func TestMarketTargetNormalized(t *testing.T) {
	target := MarketTarget{
		Exchange:  " binance ",
		AssetType: " SPOT ",
		Pair: Pair{
			Base:  " btc ",
			Quote: " usdt ",
		},
	}

	got := target.Normalized()
	if got.Exchange != "binance" {
		t.Fatalf("expected normalized exchange, got %q", got.Exchange)
	}
	if got.AssetType != "spot" {
		t.Fatalf("expected normalized asset type, got %q", got.AssetType)
	}
	if got.Pair.Base != "BTC" || got.Pair.Quote != "USDT" {
		t.Fatalf("expected normalized pair BTC/USDT, got %+v", got.Pair)
	}
}

func TestMarketTargetSymbol(t *testing.T) {
	target := MarketTarget{
		Pair: Pair{Base: "ETH", Quote: "USD"},
	}

	if got := target.Symbol(); got != "ETH/USD" {
		t.Fatalf("expected ETH/USD, got %q", got)
	}
}

func TestOrderbookSnapshotBestLevels(t *testing.T) {
	snapshot := OrderbookSnapshot{
		Bids: []OrderbookLevel{
			{Price: 100, Amount: 2},
			{Price: 99, Amount: 1},
		},
		Asks: []OrderbookLevel{
			{Price: 101, Amount: 3},
			{Price: 102, Amount: 4},
		},
	}

	bestBid, ok := snapshot.BestBid()
	if !ok {
		t.Fatal("expected best bid")
	}
	if bestBid.Price != 100 {
		t.Fatalf("expected best bid 100, got %f", bestBid.Price)
	}

	bestAsk, ok := snapshot.BestAsk()
	if !ok {
		t.Fatal("expected best ask")
	}
	if bestAsk.Price != 101 {
		t.Fatalf("expected best ask 101, got %f", bestAsk.Price)
	}
}
