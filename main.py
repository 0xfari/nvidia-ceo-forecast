#!/usr/bin/env python3
"""Forecast Polymarket's "Next CEO of NVIDIA?" Yes prices, 240 minutes ahead.

Per market, a persistence forecast around the checkpoint price x, with a
spread from the market's own recent volatility:

    q_tau(h) = clamp(x + adj + z_tau * sigma * h**0.40, 0, 1), rounded 6 decimals

sigma is a blend of the population standard deviation of the market's
one-minute price moves over the last 2 hours (weight 0.7) and the last
6 hours (weight 0.3), each winsorized at +/-0.025 so a single jump in the
estimation window does not blow the spread up. Blending two windows makes
the estimate steadier than either alone. The exponent 0.40 (rather than
the random-walk 0.5) reflects that these prices mean-revert: their
multi-step variance grows slower than the horizon. No drift: Polymarket
prices are a martingale, and every drift we tried on the practice cases
made the pinball loss worse.

adj is a partial sum-shrink, the one correction that paid on the practice
cases. The event's markets are mutually exclusive, so their prices should
sum to about 1; at the checkpoints the sum usually sits above 1.05. When
it does, the excess (S - 1.05) is absorbed only by the markets sitting
above their own 6-hour median, in proportion to how far above it they sit:

    adj_i = -1.25 * (S - 1.05) * w_i / W,  w_i = max(0, x_i - median(prices_i[-360:]))
    (adj_i = 0 when S <= 1.05 or no market sits above its 6-hour median)

Practice loss 0.263446 on the six practice cases (house baseline 0.363589,
previous version 0.270546).

Standard library only, no network, deterministic: the same case always
writes the same bytes.
"""

import json
import math
import os
import statistics

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]
# (window minutes, weight) of each volatility estimate; weights sum to 1.
WINDOWS = [(120, 0.7), (360, 0.3)]
CLIP = 0.025
ALPHA = 0.40
# Sum-shrink: target sum and absorption strength (see module docstring).
SUM_TARGET = 1.05
SUM_K = 1.25
SUM_MEDIAN_WINDOW = 360


def price6(x):
    """x clamped to [0, 1] and rounded to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0.0


def _winsor_std(prices, window):
    """Winsorized std of 1-minute moves over the last `window` minutes."""
    seg = prices[-window:]
    diffs = []
    for a, b in zip(seg, seg[1:]):
        d = b - a
        if d > CLIP:
            d = CLIP
        elif d < -CLIP:
            d = -CLIP
        diffs.append(d)
    n = len(diffs)
    if n < 2:
        return 0.0
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / n
    return math.sqrt(var)


def sigma(prices):
    """Blended winsorized volatility over the recent windows."""
    return sum(w * _winsor_std(prices, win) for win, w in WINDOWS)


def adjustments(markets):
    """Per-market median shift from the sum excess (0 for most cases)."""
    xs = [m["prices"][-1] for m in markets]
    total = sum(xs)
    adj = {m["id"]: 0.0 for m in markets}
    if total <= SUM_TARGET:
        return adj
    weights = {}
    weight_total = 0.0
    for m in markets:
        w = max(0.0, m["prices"][-1] - statistics.median(m["prices"][-SUM_MEDIAN_WINDOW:]))
        weights[m["id"]] = w
        weight_total += w
    if weight_total <= 0.0:
        return adj
    for m in markets:
        adj[m["id"]] = -SUM_K * (total - SUM_TARGET) * weights[m["id"]] / weight_total
    return adj


def forecast(market, horizon, adj):
    prices = market["prices"]
    if not prices:
        raise ValueError(f"market {market['id']} has no prices")
    x = prices[-1]
    sig = sigma(prices)
    rows = []
    for h in range(1, horizon + 1):
        s = sig * (h ** ALPHA)
        rows.append([price6(x + adj + z * s) for z in Z])
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in inputs:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        if list(case["quantiles"]) != QUANTILES:
            raise ValueError(f"{name} asks for quantiles {case['quantiles']}")
        adj = adjustments(case["markets"])
        forecasts = [
            {"id": m["id"], "q": forecast(m, case["horizon_minutes"], adj[m["id"]])}
            for m in case["markets"]
        ]
        out = os.path.join(OUTPUT_DIR, f"{case_id}.out")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
