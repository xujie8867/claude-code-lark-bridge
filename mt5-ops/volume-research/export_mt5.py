"""Run on the Windows server (same machine as the MT5 terminal), read-only.

  pip install MetaTrader5 pandas
  python export_mt5.py bars  --symbols XAUUSD EURUSD GBPUSD USDJPY AUDUSD US500 USTEC \
                             --timeframe M15 --start 2021-01-01 --out data
  python export_mt5.py deals --start 2026-08-01 --out data           # live deal history
  python export_mt5.py costs --start 2026-08-01 --out data           # P4 cost audit

Nothing here sends orders. Symbol names differ by broker (e.g. 'US500' vs 'SP500');
check Market Watch and pass the exact names.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:  # allows --help on non-Windows machines
    mt5 = None

TF = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "M30": "TIMEFRAME_M30",
      "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1"}


def init():
    if mt5 is None:
        raise SystemExit("MetaTrader5 package not available: run this on the Windows MT5 machine")
    if not mt5.initialize():
        raise SystemExit(f"mt5.initialize() failed: {mt5.last_error()}")
    acc = mt5.account_info()
    print(f"connected: account {acc.login} server {acc.server} (trade_mode={acc.trade_mode})")


def export_bars(args):
    tf = getattr(mt5, TF[args.timeframe])
    start = datetime.fromisoformat(args.start)
    end = datetime.now() + timedelta(days=1)
    rows = []
    for sym in args.symbols:
        if not mt5.symbol_select(sym, True):
            print(f"!! {sym}: not available on this server, skipped")
            continue
        r = mt5.copy_rates_range(sym, tf, start, end)
        if r is None or len(r) == 0:
            print(f"!! {sym}: no bars ({mt5.last_error()}) — scroll the chart back / raise 'Max bars in chart'")
            continue
        df = pd.DataFrame(r)
        df["time"] = pd.to_datetime(df["time"], unit="s")  # broker server time
        info = mt5.symbol_info(sym)
        df = df.rename(columns={"tick_volume": "tick_volume", "spread": "spread_points"})
        path = os.path.join(args.out, f"{sym}_{args.timeframe}.csv")
        df[["time", "open", "high", "low", "close", "tick_volume", "spread_points"]].to_csv(path, index=False)
        rows.append({"symbol": sym, "bars": len(df), "from": df["time"].iloc[0], "to": df["time"].iloc[-1],
                     "point": info.point, "contract_size": info.trade_contract_size,
                     "median_spread_price": df["spread_points"].median() * info.point})
        print(f"{sym}: {len(df)} bars -> {path}")
    meta = pd.DataFrame(rows)
    meta.to_csv(os.path.join(args.out, f"symbols_{args.timeframe}.csv"), index=False)
    print("\nNOTE: median_spread_price is the bar spread only. Add commission per unit to get cost_rt"
          "\n      (e.g. $7/lot round trip on 100 oz gold = 0.07 per oz). Use 'costs' for measured values.")


def get_deals(start):
    deals = mt5.history_deals_get(start, datetime.now() + timedelta(days=1))
    if deals is None:
        raise SystemExit(f"history_deals_get failed: {mt5.last_error()}")
    df = pd.DataFrame([d._asdict() for d in deals])
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def export_deals(args):
    df = get_deals(datetime.fromisoformat(args.start))
    if df.empty:
        print("no deals")
        return
    df["event"] = "deal"
    df = df.rename(columns={"position_id": "position_id"})
    cols = ["time", "event", "ticket", "position_id", "symbol", "type", "entry", "volume", "price",
            "profit", "commission", "swap", "magic", "comment"]
    path = os.path.join(args.out, "deals_live.csv")
    df[cols].to_csv(path, index=False)
    print(f"{len(df)} deals -> {path}")
    print(df[df["entry"] == 0].groupby(["magic", "symbol"]).size().rename("entries").to_string())


def export_costs(args):
    """Measured round-trip cost per symbol from real fills:
    spread paid (ask-bid at fill) + adverse slippage vs the quote + commission per unit."""
    df = get_deals(datetime.fromisoformat(args.start))
    df = df[df["type"].isin([0, 1])]
    rows = []
    for _, d in df.iterrows():
        t = d["time"].to_pydatetime()
        ticks = mt5.copy_ticks_range(d["symbol"], t - timedelta(seconds=5), t + timedelta(seconds=1), mt5.COPY_TICKS_INFO)
        if ticks is None or len(ticks) == 0:
            continue
        last = ticks[-1]
        bid, ask = float(last["bid"]), float(last["ask"])
        mid = (bid + ask) / 2
        side = 1 if d["type"] == 0 else -1
        info = mt5.symbol_info(d["symbol"])
        units = d["volume"] * info.trade_contract_size
        rows.append({"symbol": d["symbol"], "time": d["time"], "magic": d["magic"], "entry": d["entry"],
                     "half_cost_vs_mid": side * (d["price"] - mid),
                     "spread": ask - bid,
                     "commission_per_unit": abs(d["commission"]) / units if units else 0.0})
    c = pd.DataFrame(rows)
    if c.empty:
        print("no ticks found around deals (tick history may be missing for that period)")
        return
    c.to_csv(os.path.join(args.out, "cost_fills.csv"), index=False)
    g = c.groupby("symbol")
    summary = pd.DataFrame({
        "fills": g.size(),
        "median_half_cost": g["half_cost_vs_mid"].median(),
        "p90_half_cost": g["half_cost_vs_mid"].quantile(0.9),
        "median_spread": g["spread"].median(),
        "commission_per_unit_per_side": g["commission_per_unit"].median(),
    })
    # round trip = 2 x (half cost vs mid) + 2 x commission per side; p90 version is the conservative one
    summary["cost_rt_median"] = 2 * summary["median_half_cost"] + 2 * summary["commission_per_unit_per_side"]
    summary["cost_rt_p90"] = 2 * summary["p90_half_cost"] + 2 * summary["commission_per_unit_per_side"]
    summary.to_csv(os.path.join(args.out, "cost_summary.csv"))
    summary.reset_index()[["symbol", "cost_rt_p90"]].rename(columns={"cost_rt_p90": "cost_rt"}) \
        .to_csv(os.path.join(args.out, "costs_measured.csv"), index=False)
    print(summary.round(4).to_string())
    print("\nDemo fills are optimistic vs real money; pre-register cost_rt_p90 (or higher), not the median.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["bars", "deals", "costs"])
    ap.add_argument("--symbols", nargs="+", default=["XAUUSD"])
    ap.add_argument("--timeframe", default="M15", choices=list(TF))
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    init()
    try:
        {"bars": export_bars, "deals": export_deals, "costs": export_costs}[args.what](args)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
