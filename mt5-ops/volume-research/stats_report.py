"""Report on one or two trade lists.

  # one trade list: summary + per-year breakdown (use for the BreakGate baseline!)
  python stats_report.py runs/breakgate_base/trades.csv --pnl pnl --n-trials 20

  # loosened variant vs baseline: judge the ADDED trades on their own
  python stats_report.py runs/ct_base/trades.csv --marginal runs/ct_mp3/trades.csv --pnl pnl_atr

Trade CSV needs at least: entry_time, direction, <pnl column>; 'symbol' optional.
Deal logs from DealLogger.mqh / export_mt5.py can be turned into this shape with
reconcile.py --dump-trades.
"""
from __future__ import annotations

import argparse

import pandas as pd

import stats


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    if "symbol" not in df:
        df["symbol"] = "?"
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline")
    ap.add_argument("--marginal", help="variant trade list to compare against baseline")
    ap.add_argument("--pnl", default="pnl")
    ap.add_argument("--n-trials", type=int, default=1)
    ap.add_argument("--match-minutes", type=int, default=0,
                    help="round entry times to N minutes before matching (0 = exact)")
    args = ap.parse_args()

    base = load(args.baseline)
    days = (base["entry_time"].max() - base["entry_time"].min()).days or 1
    print("== baseline ==\n" + stats.fmt(stats.summarize(base[args.pnl], args.n_trials, days)))
    print("\n== baseline by year (is the edge one regime?) ==")
    print(stats.by_year(base, args.pnl).round(3).to_string())

    if args.marginal:
        var = load(args.marginal)
        if args.match_minutes:
            for df in (base, var):
                df["entry_time"] = df["entry_time"].dt.round(f"{args.match_minutes}min")
        print("\n== variant total ==\n" + stats.fmt(stats.summarize(var[args.pnl], args.n_trials, days)))
        m = stats.marginal(base, var, pnl_col=args.pnl)
        print(f"\n== marginal decomposition ==")
        for k in ("shared", "added", "displaced"):
            print(f"{k:>9}: " + stats.fmt(m[k]))
        print("\nverdict hint: a loosening only helps if 'added' is positive with t>=2 on its own,"
              "\nand 'displaced' (baseline trades lost) was not carrying the edge.")


if __name__ == "__main__":
    main()
