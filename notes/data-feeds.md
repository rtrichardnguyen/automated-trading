# Data Feed Pros And Cons

This note compares the data feeds as they exist in this repository today, not as idealized vendor integrations.

## 1. Historic CSV Feed (`data.py` + `download.py`)

This is the backtesting path built around `HistoricCSVDataHandler` and locally stored CSVs downloaded from Yahoo Finance.

### Pros

- Most stable and deterministic option for backtests. Once the CSV is on disk, runs are reproducible.
- Simple to inspect and debug. You can open the CSV and verify the exact bars the strategy saw.
- Supports `adj_close`, which matches how the rest of the portfolio and strategy code already reads prices.
- Uses a combined index across symbols, then forward-fills missing timestamps before computing `returns`.
- The forward-fill plus `pct_change()` behavior makes multi-symbol comparisons easier because all symbols share the same timeline.
- No runtime dependency on a live API once data has been downloaded.

### Cons

- The current downloader is limited. `download.py` pulls daily Yahoo data and drops `high` and `low`, so the feed is not a full OHLCV source in practice.
- Data must be refreshed manually. It is easy to backtest on stale files without noticing.
- Forward-filling can hide missing data. A padded bar creates a flat price and therefore a zero return, which is convenient but not always economically correct.
- This is only for backtesting and simulation. It is not a live feed.
- Yahoo CSVs are a convenience source, not a production market data path.

## 2. Alpaca Live Feed (`alpaca_data.py`)

This is the live streaming path using Alpaca bar messages over WebSocket.

### Pros

- Closest path to real live trading in this repo.
- Event-driven structure matches the rest of the system well. Incoming bars can flow directly into `MarketEvent`s.
- No need to pre-download files.
- Raw live bar fields are straightforward: open, high, low, close, volume.

### Cons

- The implementation is still a skeleton and is not production-ready in its current state.
- It does not currently behave like `data.py` with respect to alignment. Bars arrive per symbol as they are received, not on a shared combined index.
- Because of that, you do not get `comb_index.union(...)`, forward-fill, and `pct_change()` semantics automatically.
- To make it behave like the CSV handler, you would need a canonical bar clock and logic to emit padded bars for symbols that did not trade at a given timestamp.
- Requires API credentials, network access, and handling for reconnects, market hours, and backfill.
- There is no true local reproducibility. The feed depends on what arrived from the vendor in real time.

## 3. Massive Historical API Feed (`massive_data.py`)

This is the historical API path using Massive aggregate bars.

### Pros

- Better fit than CSV when you want vendor-backed historical bars without managing local files first.
- More flexible than the current Yahoo downloader because it can request configurable `timespan` and `multiplier`.
- Richer bar payload than the CSV path: open, high, low, close, volume, VWAP, transactions, and OTC flag.
- The current design is moving toward the same shape as `data.py`: build per-symbol DataFrames, union indexes, forward-fill, then compute `pct_change()`.
- Good candidate for intraday backtesting once completed.

### Cons

- Still in progress. It is not yet as complete or battle-tested as the CSV handler.
- Like any API-backed source, it depends on credentials, network availability, and vendor response behavior.
- Unless you explicitly source adjusted prices, this feed is effectively working off raw close prices.
- Empty or sparse symbol histories need careful handling, otherwise index-building and forward-fill logic can fail or produce misleading padded rows.
- More moving parts than local CSVs, so debugging is less transparent.

## Forward Fill And Returns

The main behavioral difference in this repo is not the `returns` formula by itself. `pct_change()` is just the vectorized version of one-step percentage return.

The bigger difference is whether the feed:

- builds one combined timestamp index across symbols
- forward-fills missing rows onto that shared index
- computes returns after alignment

Right now:

- `data.py` does all three.
- `massive_data.py` is being moved in that direction.
- `alpaca_data.py` does not naturally work that way yet because live bars arrive asynchronously by symbol.

## Practical Recommendation

- Use the CSV feed when you want the cleanest and most reproducible backtest path.
- Use the Massive feed when you want API-based historical data and are willing to finish and harden the handler.
- Use the Alpaca feed only for live trading work, and assume more engineering is needed before it matches the backtest feed semantics.
