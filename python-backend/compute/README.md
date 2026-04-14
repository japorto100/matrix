# python-compute

Python Compute Plane — indicator calculations, finance data, geopolitical signals.

## Services

| Service | Port | Description |
|---------|------|-------------|
| `indicator-service` | 8092 | Technical indicators (EMA/RSI/ATR/BB via Rust hot-paths) |
| `finance-bridge` | 8081 | Finance data bridge (yfinance, market data) |
| `geopolitical-soft-signals` | 8091 | Geo soft-signal computation |

## Venv strategy

Currently uses `python-backend/.venv` (shared with python-backend root) because the
`tradeviewfusion-rust-core` Rust extension must be built once and shared.

Future (Phase 19-20): standalone `python-compute/.venv` after multi-venv Rust build support.

## Shared code access

All services access shared `ml_ai/` and `services/_shared/` via `sys.path.insert`:
```python
PYTHON_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # → python-backend/
sys.path.insert(0, str(PYTHON_BACKEND_ROOT))
```
