"""P1: compare live deals with tester deals over the same period.

Both inputs use the DealLogger.mqh / export_mt5.py deal schema:
  time,event,ticket,position_id,symbol,type,entry,volume,price,profit,commission,swap,magic,comment[,bid,ask]
(type: 0=buy 1=sell; entry: 0=in 1=out 2=inout 3=out_by; event: deal|skip)

  python reconcile.py --live deals_live.csv --tester deals_tester.csv \
      --magic 20261 --tolerance-min 20 --out runs/p1

Outputs
  missed_in_live.csv   entries the tester made that live did not  -> the volume gap
  extra_in_live.csv    entries live made that the tester did not
  matched.csv          paired entries with entry-price difference (slippage view)
  skip_reasons.csv     live 'skip' events grouped by reason (if DealLogger_Skip is used)

  python reconcile.py --live deals_live.csv --dump-trades trades_live.csv
      -> collapse deals into one row per position (entry_time,direction,pnl,...) for stats_report.py
"""
from __future__ import annotations

import argparse
import os

import pandas as pd


def load_deals(path: str, magic: int | None) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"])
    if "event" not in df:
        df["event"] = "deal"
    if magic is not None and "magic" in df:
        df = df[(df["magic"] == magic) | (df["event"] == "skip")]
    return df.sort_values("time").reset_index(drop=True)


def entries(df: pd.DataFrame) -> pd.DataFrame:
    e = df[(df["event"] == "deal") & (df["entry"] == 0) & (df["type"].isin([0, 1]))].copy()
    e["direction"] = e["type"].map({0: 1, 1: -1})
    return e[["time", "symbol", "direction", "price", "volume", "position_id"]].reset_index(drop=True)


def to_trades(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["event"] == "deal"]
    rows = []
    for pid, g in d.groupby("position_id"):
        ins = g[g["entry"] == 0]
        if ins.empty:
            continue
        first = ins.iloc[0]
        net = (g["profit"] + g.get("commission", 0) + g.get("swap", 0)).sum()
        rows.append({"symbol": first["symbol"], "entry_time": first["time"],
                     "exit_time": g["time"].max(), "direction": 1 if first["type"] == 0 else -1,
                     "volume": ins["volume"].sum(), "pnl": net})
    return pd.DataFrame(rows).sort_values("entry_time")


def match(live: pd.DataFrame, tester: pd.DataFrame, tol: pd.Timedelta):
    used = set()
    pairs, missed = [], []
    for _, t in tester.iterrows():
        cand = live[(live["symbol"] == t["symbol"]) & (live["direction"] == t["direction"])
                    & ((live["time"] - t["time"]).abs() <= tol) & (~live.index.isin(used))]
        if cand.empty:
            missed.append(t)
            continue
        j = (cand["time"] - t["time"]).abs().idxmin()
        used.add(j)
        l = live.loc[j]
        pairs.append({"symbol": t["symbol"], "direction": t["direction"],
                      "tester_time": t["time"], "live_time": l["time"],
                      "delay_s": (l["time"] - t["time"]).total_seconds(),
                      "tester_price": t["price"], "live_price": l["price"],
                      "adverse_px": t["direction"] * (l["price"] - t["price"])})
    extra = live[~live.index.isin(used)]
    return pd.DataFrame(pairs), pd.DataFrame(missed), extra


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", required=True)
    ap.add_argument("--tester")
    ap.add_argument("--magic", type=int)
    ap.add_argument("--tolerance-min", type=int, default=20)
    ap.add_argument("--dump-trades")
    ap.add_argument("--out", default="runs/p1")
    args = ap.parse_args()

    live = load_deals(args.live, args.magic)
    if args.dump_trades:
        to_trades(live).to_csv(args.dump_trades, index=False)
        print(f"trades written to {args.dump_trades}")
        if not args.tester:
            return

    tester = load_deals(args.tester, args.magic)
    start, end = live["time"].min(), live["time"].max()
    tol = pd.Timedelta(minutes=args.tolerance_min)
    tester = tester[(tester["time"] >= start - tol) & (tester["time"] <= end + tol)]
    le, te = entries(live), entries(tester)
    pairs, missed, extra = match(le, te, tol)

    os.makedirs(args.out, exist_ok=True)
    pairs.to_csv(os.path.join(args.out, "matched.csv"), index=False)
    missed.to_csv(os.path.join(args.out, "missed_in_live.csv"), index=False)
    extra.to_csv(os.path.join(args.out, "extra_in_live.csv"), index=False)

    days = max((end - start).days, 1)
    print(f"period {start} -> {end} ({days} d)")
    print(f"tester entries {len(te)} ({len(te)/days:.2f}/d) | live entries {len(le)} ({len(le)/days:.2f}/d)")
    print(f"matched {len(pairs)} | missed in live {len(missed)} | extra in live {len(extra)}")
    if len(pairs):
        print(f"median delay {pairs['delay_s'].median():.0f}s | mean adverse entry price {pairs['adverse_px'].mean():.4f}")
    if len(missed):
        m = pd.DataFrame(missed)
        print("\nmissed entries by broker hour (look for gaps: session filter, restarts, rollover):")
        print(m.groupby(m["time"].dt.hour).size().to_string())
        print("\nmissed entries by weekday:")
        print(m.groupby(m["time"].dt.day_name()).size().to_string())
    skips = live[live["event"] == "skip"]
    if len(skips):
        sr = skips.groupby("comment").size().sort_values(ascending=False)
        sr.to_csv(os.path.join(args.out, "skip_reasons.csv"))
        print("\nlive skip reasons:\n" + sr.to_string())
    print(f"\nwritten to {args.out}/  — next: for each missed entry, check the terminal/EA journal at that time")


if __name__ == "__main__":
    main()
