"""Trade-level statistics shared by every script in this folder.

Only depends on numpy/pandas (no scipy). All functions take a pandas Series of
per-trade net P&L (costs already deducted) unless noted.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329


def profit_factor(pnl: pd.Series) -> float:
    gains = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    if losses == 0:
        return math.inf if gains > 0 else float("nan")
    return float(gains / losses)


def t_stat(pnl: pd.Series) -> float:
    n = len(pnl)
    if n < 2:
        return float("nan")
    sd = pnl.std(ddof=1)
    return float(pnl.mean() / sd * math.sqrt(n)) if sd > 0 else float("nan")


def max_drawdown(pnl: pd.Series) -> float:
    equity = pnl.cumsum()
    return float((equity.cummax() - equity).max()) if len(equity) else 0.0


def deflated_sharpe(pnl: pd.Series, n_trials: int, sr_trials_var: float | None = None) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014), per-trade SR.

    n_trials: how many variants were tried for this research question
              (count every pre-registered and exploratory run honestly).
    sr_trials_var: variance of per-trade SR across those trials. If unknown,
              a conservative default of (1/n_obs) is used (SR estimation noise).
    """
    n = len(pnl)
    if n < 3 or pnl.std(ddof=1) == 0:
        return float("nan")
    sr = pnl.mean() / pnl.std(ddof=1)
    skew = float(pnl.skew())
    kurt = float(pnl.kurt()) + 3.0  # pandas gives excess kurtosis
    if sr_trials_var is None:
        sr_trials_var = 1.0 / n
    if n_trials <= 1:
        sr0 = 0.0
    else:
        sr0 = math.sqrt(sr_trials_var) * (
            (1 - EULER_GAMMA) * _N.inv_cdf(1 - 1.0 / n_trials)
            + EULER_GAMMA * _N.inv_cdf(1 - 1.0 / (n_trials * math.e))
        )
    denom = 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr
    if denom <= 0:
        return float("nan")
    return float(_N.cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(denom)))


def summarize(pnl: pd.Series, n_trials: int = 1, days: float | None = None) -> dict:
    out = {
        "trades": int(len(pnl)),
        "net": float(pnl.sum()),
        "mean": float(pnl.mean()) if len(pnl) else float("nan"),
        "win_rate": float((pnl > 0).mean()) if len(pnl) else float("nan"),
        "PF": profit_factor(pnl),
        "t": t_stat(pnl),
        "maxDD": max_drawdown(pnl),
        "DSR": deflated_sharpe(pnl, n_trials),
    }
    if days:
        out["trades_per_day"] = len(pnl) / days
    return out


def by_year(trades: pd.DataFrame, pnl_col: str = "pnl", time_col: str = "entry_time") -> pd.DataFrame:
    """Per-calendar-year breakdown: is the edge spread out, or one regime?"""
    g = trades.groupby(trades[time_col].dt.year)[pnl_col]
    return pd.DataFrame({
        "trades": g.size(),
        "net": g.sum(),
        "PF": g.apply(profit_factor),
        "t": g.apply(t_stat),
    })


def marginal(baseline: pd.DataFrame, variant: pd.DataFrame,
             keys=("symbol", "entry_time", "direction"), pnl_col: str = "pnl") -> dict:
    """Split a loosened variant into: trades shared with baseline, trades it ADDS,
    and baseline trades it DISPLACES. Judge a loosening by the added set alone."""
    keys = list(keys)
    b = baseline[keys + [pnl_col]].copy()
    v = variant[keys + [pnl_col]].copy()
    merged = v.merge(b[keys].assign(_in_base=True), on=keys, how="left")
    added = merged[merged["_in_base"].isna()][pnl_col]
    shared = merged[merged["_in_base"].notna()][pnl_col]
    displaced = b.merge(v[keys].assign(_in_var=True), on=keys, how="left")
    displaced = displaced[displaced["_in_var"].isna()][pnl_col]
    return {
        "shared": summarize(shared),
        "added": summarize(added),
        "displaced": summarize(displaced),
    }


def fmt(d: dict) -> str:
    parts = []
    for k, v in d.items():
        if isinstance(v, float):
            parts.append(f"{k}={v:,.3f}" if abs(v) < 1000 else f"{k}={v:,.0f}")
        else:
            parts.append(f"{k}={v}")
    return "  ".join(parts)
