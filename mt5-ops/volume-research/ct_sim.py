"""Bar-based simulator for a CT-style z-score strategy, used for P2 and P3.

Logic (all parameters are CLI flags so the real CT rules can be mirrored):
  z_t = (close_t - SMA_N) / STD_N            on the bar series (default M15, N=96)
  signal at the CLOSE of bar t when |z_t| >= z_entry
      (--require-cross: only when |z| crosses the threshold, not every bar above it)
  direction = sign(z) for --mode trend, -sign(z) for --mode revert
  fill at the OPEN of bar t+1
  exits (whichever first): SL / TP as ATR multiples (checked intrabar, SL first),
      z back through --z-exit, or --max-bars time stop.
  --max-positions caps concurrent positions per symbol; signals that arrive while
      at the cap are logged as SKIPPED (this is the P2 measurement).

P&L is reported in two units:
  pnl      : price units per 1 unit of the instrument, minus round-trip cost
  pnl_atr  : pnl / ATR at entry  -> comparable across symbols (portfolio stats use this)

Input CSV per symbol (from export_mt5.py): time,open,high,low,close[,spread]
Cost: --cost SYMBOL=price_units (round trip), else spread column * point * 2 is NOT
assumed; you must pass a cost or --cost-from-spread with --point.

Examples
  # P2: how many CT signals are skipped because a position is already open?
  python ct_sim.py --data data/XAUUSD_M15.csv --symbol XAUUSD --cost XAUUSD=0.90 \
      --max-positions 1 --out runs/ct_base

  # P2 variant: allow 3 concurrent positions, then compare with stats_report.py --marginal
  python ct_sim.py ... --max-positions 3 --out runs/ct_mp3

  # P3: frozen parameters on a basket (no per-symbol tuning!)
  python ct_sim.py --data data/*_M15.csv --cost-file costs.csv --out runs/ct_basket
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

import stats


@dataclass
class Params:
    lookback: int = 96
    z_entry: float = 1.0
    z_exit: float | None = 0.0
    mode: str = "trend"
    require_cross: bool = True
    max_positions: int = 1
    sl_atr: float | None = 2.0
    tp_atr: float | None = None
    max_bars: int | None = 96
    atr_len: int = 14
    session_start: int | None = None  # broker-hour filter, inclusive
    session_end: int | None = None    # exclusive


def load_bars(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"])
    return df.sort_values("time").reset_index(drop=True)


def indicators(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    c = df["close"]
    mean = c.rolling(p.lookback).mean()
    std = c.rolling(p.lookback).std(ddof=0)
    df = df.copy()
    df["z"] = (c - mean) / std
    prev_c = c.shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_c).abs(), (df["low"] - prev_c).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(p.atr_len).mean()
    return df


def simulate(df: pd.DataFrame, symbol: str, cost: float, p: Params) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = indicators(df, p)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    z, atr = df["z"].to_numpy(), df["atr"].to_numpy()
    hours = df["time"].dt.hour.to_numpy()

    open_pos: list[dict] = []
    trades, signals = [], []

    for i in range(1, len(df) - 1):
        # 1) manage open positions on bar i (intrabar SL/TP, then close-based exits)
        still = []
        for pos in open_pos:
            d = pos["dir"]
            exit_px, reason = None, None
            if pos["sl"] is not None and ((d > 0 and l[i] <= pos["sl"]) or (d < 0 and h[i] >= pos["sl"])):
                exit_px, reason = pos["sl"], "sl"
            elif pos["tp"] is not None and ((d > 0 and h[i] >= pos["tp"]) or (d < 0 and l[i] <= pos["tp"])):
                exit_px, reason = pos["tp"], "tp"
            elif p.z_exit is not None and not np.isnan(z[i]) and d * z[i] * (1 if p.mode == "trend" else -1) <= p.z_exit:
                exit_px, reason = c[i], "z"
            elif p.max_bars is not None and i - pos["i"] >= p.max_bars:
                exit_px, reason = c[i], "time"
            if exit_px is None:
                still.append(pos)
                continue
            gross = d * (exit_px - pos["px"])
            trades.append({
                "symbol": symbol, "entry_time": pos["t"], "exit_time": t[i], "direction": d,
                "entry": pos["px"], "exit": exit_px, "reason": reason, "bars": i - pos["i"],
                "gross": gross, "pnl": gross - cost, "atr": pos["atr"],
                "pnl_atr": (gross - cost) / pos["atr"],
            })
        open_pos = still

        # 2) signal at close of bar i, fill at open of bar i+1
        if np.isnan(z[i]) or np.isnan(atr[i]) or abs(z[i]) < p.z_entry:
            continue
        if p.require_cross and not np.isnan(z[i - 1]) and abs(z[i - 1]) >= p.z_entry and np.sign(z[i - 1]) == np.sign(z[i]):
            continue
        if p.session_start is not None and not (p.session_start <= hours[i] < (p.session_end or 24)):
            continue
        d = int(np.sign(z[i])) * (1 if p.mode == "trend" else -1)
        taken = len(open_pos) < p.max_positions
        signals.append({"symbol": symbol, "time": t[i], "z": z[i], "direction": d,
                        "taken": taken, "open_positions": len(open_pos)})
        if not taken:
            continue
        px = o[i + 1]
        open_pos.append({
            "i": i + 1, "t": t[i + 1], "px": px, "dir": d, "atr": atr[i],
            "sl": px - d * p.sl_atr * atr[i] if p.sl_atr else None,
            "tp": px + d * p.tp_atr * atr[i] if p.tp_atr else None,
        })

    tr = pd.DataFrame(trades)
    sg = pd.DataFrame(signals)
    for frame, col in ((tr, "entry_time"), (tr, "exit_time"), (sg, "time")):
        if len(frame):
            frame[col] = pd.to_datetime(frame[col])
    return tr, sg


def parse_costs(args) -> dict[str, float]:
    costs = {}
    if args.cost_file:
        cf = pd.read_csv(args.cost_file)
        costs.update(dict(zip(cf["symbol"], cf["cost_rt"])))
    for item in args.cost or []:
        k, v = item.split("=")
        costs[k] = float(v)
    return costs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", nargs="+", required=True, help="CSV paths or globs, file name must start with SYMBOL_")
    ap.add_argument("--symbol", help="override symbol (single file only)")
    ap.add_argument("--cost", action="append", help="SYMBOL=round_trip_cost_in_price_units")
    ap.add_argument("--cost-file", help="CSV with columns symbol,cost_rt")
    ap.add_argument("--lookback", type=int, default=96)
    ap.add_argument("--z-entry", type=float, default=1.0)
    ap.add_argument("--z-exit", type=float, default=0.0, help="use 'nan' to disable")
    ap.add_argument("--mode", choices=["trend", "revert"], default="trend")
    ap.add_argument("--no-require-cross", action="store_true")
    ap.add_argument("--max-positions", type=int, default=1)
    ap.add_argument("--sl-atr", type=float, default=2.0, help="0 disables")
    ap.add_argument("--tp-atr", type=float, default=0.0, help="0 disables")
    ap.add_argument("--max-bars", type=int, default=96, help="0 disables")
    ap.add_argument("--session", help="broker hours START-END, e.g. 1-22")
    ap.add_argument("--n-trials", type=int, default=1, help="honest count of variants tried, for DSR")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ss = se = None
    if args.session:
        ss, se = (int(x) for x in args.session.split("-"))
    p = Params(
        lookback=args.lookback, z_entry=args.z_entry,
        z_exit=None if str(args.z_exit) == "nan" else args.z_exit,
        mode=args.mode, require_cross=not args.no_require_cross, max_positions=args.max_positions,
        sl_atr=args.sl_atr or None, tp_atr=args.tp_atr or None, max_bars=args.max_bars or None,
        session_start=ss, session_end=se,
    )
    costs = parse_costs(args)
    paths = sorted({f for pat in args.data for f in glob.glob(pat)})
    if not paths:
        raise SystemExit("no data files matched")

    os.makedirs(args.out, exist_ok=True)
    all_tr, all_sg, rows = [], [], []
    for path in paths:
        sym = args.symbol or os.path.basename(path).split("_")[0]
        if sym not in costs:
            raise SystemExit(f"no cost for {sym}: pass --cost {sym}=X or --cost-file (never assume zero cost)")
        bars = load_bars(path)
        tr, sg = simulate(bars, sym, costs[sym], p)
        days = (bars["time"].iloc[-1] - bars["time"].iloc[0]).days or 1
        all_tr.append(tr)
        all_sg.append(sg)
        s = stats.summarize(tr["pnl_atr"], args.n_trials, days) if len(tr) else {"trades": 0}
        skipped = int((~sg["taken"]).sum()) if len(sg) else 0
        s.update({"symbol": sym, "signals": len(sg), "skipped": skipped,
                  "skipped_pct": skipped / len(sg) if len(sg) else float("nan"),
                  "gross_PF": stats.profit_factor(tr["gross"]) if len(tr) else float("nan")})
        rows.append(s)

    tr = pd.concat(all_tr, ignore_index=True)
    sg = pd.concat(all_sg, ignore_index=True)
    tr.to_csv(os.path.join(args.out, "trades.csv"), index=False)
    sg.to_csv(os.path.join(args.out, "signals.csv"), index=False)
    per_sym = pd.DataFrame(rows).set_index("symbol")
    per_sym.to_csv(os.path.join(args.out, "per_symbol.csv"))

    # portfolio: equal ATR-risk per trade, aggregate by exit day
    daily = tr.groupby([tr["exit_time"].dt.normalize(), "symbol"])["pnl_atr"].sum().unstack(fill_value=0)
    port = stats.summarize(tr["pnl_atr"], args.n_trials)
    corr = daily.corr() if daily.shape[1] > 1 else pd.DataFrame()
    corr.to_csv(os.path.join(args.out, "daily_corr.csv"))
    yearly = stats.by_year(tr, "pnl_atr")
    yearly.to_csv(os.path.join(args.out, "by_year.csv"))
    with open(os.path.join(args.out, "params.json"), "w") as f:
        json.dump({"params": p.__dict__, "costs": costs, "files": paths}, f, indent=2, default=str)

    pd.set_option("display.width", 200)
    print("== per symbol (pnl in ATR units, net of cost) ==")
    print(per_sym.round(3).to_string())
    print("\n== portfolio ==\n" + stats.fmt(port))
    print("\n== by year ==\n" + yearly.round(3).to_string())
    if len(corr):
        off = corr.where(~np.eye(len(corr), dtype=bool)).stack()
        print(f"\nmean pairwise daily correlation: {off.mean():.3f}")
    print(f"\nwritten to {args.out}/")


if __name__ == "__main__":
    main()
