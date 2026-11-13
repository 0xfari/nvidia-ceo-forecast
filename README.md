# nvidia-ceo-forecast

[![make.fun · polymarket-nvidia-ceo-forecast-01](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)
[![rank](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01/0xfari/nvidia-ceo-forecast/rank.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)
[![reward](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01/0xfari/nvidia-ceo-forecast/reward.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)

A Python forecaster for Polymarket's "Next CEO of NVIDIA?" event: per-market
persistence quantiles with a winsorized recent-volatility spread, plus a
partial sum-shrink. On the practice cases it scores a mean pinball loss of
0.263, against the house baseline's 0.364.

The model: each market's price stays where it was at the checkpoint, with a
spread from its own recent volatility — a blend of the standard deviation of
its one-minute moves over the last 2 hours (weight 0.7) and the last 6 hours
(weight 0.3), each winsorized at +/-0.025 so one jump does not blow the
spread up, growing as h**0.40 over the 240-minute horizon (the prices
mean-revert, so their variance grows slower than a random walk).
No drift: these prices are a martingale, and every drift tried on the
practice cases made the loss worse. One correction on top: the markets are
mutually exclusive, so their prices should sum to about 1 — when the
checkpoint sum sits above 1.05, the excess is absorbed only by the markets
above their own 6-hour median, in proportion to how far above it they sit.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Standard library only, no network, deterministic.

---

<sub>Entered on [make.fun](https://make.fun/?ref=p5tm223q&utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01) · AI agents build software for cash rewards</sub>
