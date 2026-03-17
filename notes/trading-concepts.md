# Trading Concepts

## VWAP (Volume Weighted Average Price)

A benchmark that calculates the average price a security has traded at throughout the day, weighted by volume.

```
VWAP = Cumulative(Price x Volume) / Cumulative(Volume)
```

- Price above VWAP → bullish bias (buyers paying more than average)
- Price below VWAP → bearish bias (sellers accepting less than average)

Intraday traders use VWAP as a dynamic support/resistance level. It resets each trading session.

As an order type, VWAP orders slice a large order into smaller pieces throughout the day, distributing execution proportionally to historical volume patterns to minimize market impact.

### Example

```
Time     Price    Volume    Price x Volume
9:30     $120     1,000     $120,000
10:00    $121     2,000     $242,000
10:30    $119     1,500     $178,500

VWAP = ($120,000 + $242,000 + $178,500) / (1,000 + 2,000 + 1,500)
     = $540,500 / 4,500
     = $120.11
```

At 10:30, price is $119 which is below VWAP ($120.11) → bearish bias, sellers are in control.

## Returns

The percentage change in price over a period.

```
Simple Return = (P_end - P_start) / P_start

Log Return = ln(P_end / P_start)
```

Log returns are additive across time (you can sum daily log returns to get a weekly return), which makes them preferred for quantitative analysis. Simple returns are additive across portfolio assets.

## Volatility

A measure of how much a security's price fluctuates over time. Typically calculated as the standard deviation of returns.

```
Volatility = std(returns)
Annualized Volatility = std(daily_returns) x sqrt(252)
```

- High volatility → larger price swings, more risk and opportunity
- Low volatility → smaller price swings, more stable

252 is the approximate number of trading days in a year. For hourly bars, multiply by sqrt(252 x 6.5).

## Skewness

Measures the asymmetry of a return distribution.

```
Skewness = E[((X - mean) / std)^3]
```

- **Positive skew**: Longer right tail, more frequent small losses but occasional large gains
- **Negative skew**: Longer left tail, more frequent small gains but occasional large losses (common in equity markets)
- **Zero skew**: Symmetric distribution

Most trading strategies have negative skew — they win often but lose big when they lose. Strategies with positive skew (like trend following) win big but lose often.

## Sharpe Ratio

Risk-adjusted return. Measures how much excess return you get per unit of volatility.

```
Sharpe = (mean(returns) - risk_free_rate) / std(returns)
Annualized Sharpe = sqrt(252) x (mean(daily_returns) - daily_risk_free) / std(daily_returns)
```

| Sharpe | Interpretation         |
|--------|------------------------|
| < 0    | Losing money           |
| 0 - 1  | Subpar risk-adjusted   |
| 1 - 2  | Good                   |
| 2 - 3  | Very good              |
| > 3    | Excellent (rare)       |

The risk-free rate is often set to 0 for simplicity or approximated using the current Treasury bill yield.
