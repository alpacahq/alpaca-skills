# Using TA-Lib in Backtest Scripts

TA-Lib (Technical Analysis Library) provides fast, correct implementations of common technical indicators. Prefer it over manual implementations when writing `run.py` — it reduces code length and eliminates common mistakes like using SMA-seeded RSI instead of Wilder's smoothing.

## Installation

```bash
# Install the C library first, then the Python wrapper
# macOS
brew install ta-lib
pip install TA-Lib

# Ubuntu / Debian
sudo apt-get install libta-lib-dev
pip install TA-Lib

# Verify
python -c "import talib; print(talib.__version__)"
```

Add to `requirements.txt`:

```text
TA-Lib>=0.4.28
```

If the C library is unavailable in the target environment, prompt the user and ask how to proceed.

## Input format

TA-Lib functions expect NumPy arrays of `float64`. When working from a pandas DataFrame, pass the underlying array:

```python
import talib
import numpy as np

close = df["c"].values.astype(float)
high  = df["h"].values.astype(float)
low   = df["l"].values.astype(float)
open_ = df["o"].values.astype(float)
```

All inputs must be the same length. TA-Lib handles the warmup period internally and returns `NaN` for leading values that cannot be computed.

## Key functions

### SMA

```python
sma50  = talib.SMA(close, timeperiod=50)
sma200 = talib.SMA(close, timeperiod=200)
```

### EMA

```python
ema12 = talib.EMA(close, timeperiod=12)
ema26 = talib.EMA(close, timeperiod=26)
```


### RSI (Wilder's smoothed)

```python
rsi14 = talib.RSI(close, timeperiod=14)
```

### MACD

```python
macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
```

`macd` = EMA(fast) − EMA(slow). `signal` = EMA of macd. `hist` = macd − signal.

### ATR (Wilder's smoothed)

```python
atr14 = talib.ATR(high, low, close, timeperiod=14)
```

### Bollinger Bands

```python
upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
```

`matype=0` is SMA. TA-Lib uses **population** std dev (divide by N), matching [reference.md — Bollinger Bands](reference.md#bollinger-bands).

### Stochastic

```python
slowk, slowd = talib.STOCH(high, low, close,
    fastk_period=14, slowk_period=3, slowk_matype=0,
    slowd_period=3, slowd_matype=0)
```

### ADX

```python
adx14 = talib.ADX(high, low, close, timeperiod=14)
```

## Attaching results to a DataFrame

```python
df["sma50"]  = talib.SMA(close, timeperiod=50)
df["sma200"] = talib.SMA(close, timeperiod=200)
df["rsi14"]  = talib.RSI(close, timeperiod=14)

upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
df["bb_upper"]  = upper
df["bb_middle"] = middle
df["bb_lower"]  = lower
```

## Warmup handling

Never generate signals on bars where indicator values are `NaN`. Drop or mask the warmup window:

```python
warmup = 200  # length of longest indicator period
df = df.iloc[warmup:].copy()
```

Warmup bars should still appear in the equity curve as flat (fully-in-cash) equity.

## Example: SMA crossover with talib

```python
import talib
import numpy as np
import pandas as pd

df = pd.read_csv("normalized/bars_SPY.csv", parse_dates=["t"])
close = df["c"].values.astype(float)

df["sma50"]  = talib.SMA(close, timeperiod=50)
df["sma200"] = talib.SMA(close, timeperiod=200)

# Drop warmup rows
df = df.dropna(subset=["sma50", "sma200"]).reset_index(drop=True)

# Crossover signals (next-open fill)
df["cross_up"]   = (df["sma50"] > df["sma200"]) & (df["sma50"].shift(1) <= df["sma200"].shift(1))
df["cross_down"] = (df["sma50"] < df["sma200"]) & (df["sma50"].shift(1) >= df["sma200"].shift(1))
```
