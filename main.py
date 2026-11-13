#!/usr/bin/env python3
"""Forecast Polymarket's "Next CEO of NVIDIA?" Yes prices, 240 minutes ahead.

Per market, a persistence forecast around the checkpoint price x, with a
spread from the market's own recent volatility:

    q_tau(h) = clamp(x + z_tau * sigma * h**0.42, 0, 1), rounded to 6 decimals

sigma is the population standard deviation of the market's one-minute price
moves over the last 2 hours, winsorized at +/-0.02 so a single jump in the
estimation window does not blow the spread up. The exponent 0.42 (rather
than the random-walk 0.5) reflects that these prices mean-revert: their
multi-step variance grows slower than the horizon. No drift: Polymarket
prices are a martingale, and every drift we tried on the practice cases
made the pinball loss worse.

Standard library only, no network, deterministic: the same case always
writes the same bytes.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]
WINDOW_MINUTES = 120
CLIP = 0.02
ALPHA = 0.42


def price6(x):
    """x clamped to [0, 1] and rounded to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0.0


def sigma(prices):
    """Winsorized std of 1-minute moves over the last WINDOW_MINUTES."""
    seg = prices[-WINDOW_MINUTES:]
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


def forecast(market, horizon):
    prices = market["prices"]
    if not prices:
        raise ValueError(f"market {market['id']} has no prices")
    x = prices[-1]
    sig = sigma(prices)
    rows = []
    for h in range(1, horizon + 1):
        s = sig * (h ** ALPHA)
        rows.append([price6(x + z * s) for z in Z])
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
        forecasts = [
            {"id": m["id"], "q": forecast(m, case["horizon_minutes"])}
            for m in case["markets"]
        ]
        out = os.path.join(OUTPUT_DIR, f"{case_id}.out")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
