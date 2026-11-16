# 主终端增加单量：研究工具包

本工具包配合《增加主终端交易单量的问题》的复核结论使用，把建议落成可以直接运行的步骤。
**所有脚本都是只读的，不会下单。** `DealLogger.mqh` 只负责写日志，不改变 EA 的交易逻辑。

## 核心思路

前四轮研究了约 20 个方向，全部 NO-GO。这些尝试都是在**造新的 edge**。
这次换一个方向：**在唯一被统计证实的 edge（CT，t≈5）上扩容**，并且先把实盘上丢掉的单找回来。

| 优先级 | 问题 | 用什么工具 | 预计耗时 |
|---|---|---|---|
| P0 | BreakGate 基线按年度拆开看，收益是不是全部来自 2025–2026 年的牛市？"反做 PF 0.05"是不是 bug？ | `stats_report.py` | 半天 |
| P1 | CT 回测每天约 3 笔，实盘为什么更少？ | `DealLogger.mqh` + `reconcile.py` | 1–2 天 |
| P2 | CT 放宽 z 几乎不加单，瓶颈是不是"同时只持一张单"？ | `ct_sim.py` 的 `skipped_pct` 指标 + `--max-positions` 参数 | 半天 |
| P3 | 把 CT 参数冻结，搬到一篮子品种上 | `ct_sim.py` 多品种模式 + 预登记模板 | 1–2 天 |
| P4 | 实测真实成本，重跑几个"差一点"的方案 | `export_mt5.py costs` | 半天 |

## 文件

| 文件 | 在哪台机器运行 | 作用 |
|---|---|---|
| `export_mt5.py` | Windows 服务器（MT5 所在机器） | 导出 K 线、实盘成交、实测成本 |
| `DealLogger.mqh` | MT5（include 进 CT） | 实盘和回测用同一种格式记录成交和被跳过的信号 |
| `reconcile.py` | 任意 | P1：逐笔对比实盘和回测的成交 |
| `ct_sim.py` | 任意 | P2/P3：CT 风格的 z 分数策略模拟器，支持多品种、多持仓，并记录被跳过的信号 |
| `stats_report.py` | 任意 | 汇总统计、分年度拆解、**新增交易的边际分解** |
| `stats.py` | — | PF、t 值、最大回撤、DSR（Bailey & López de Prado）、边际分解 |
| `prereg-ct-volume-TEMPLATE.md` | — | P2/P3 的预登记模板 |

依赖：`pip install pandas numpy`；Windows 上导出数据还需要 `MetaTrader5`。

## 运行顺序

### P0：先审视基线（半天）
```bash
# BreakGate 的成交（MT5 历史里按它的 magic 过滤）→ 一行一单 → 分年度
python export_mt5.py deals --start 2021-01-01 --out data          # Windows 上运行
python reconcile.py --live data/deals_live.csv --magic <BreakGate magic> --dump-trades runs/bg_trades.csv
python stats_report.py runs/bg_trades.csv --n-trials 20
```
如果净利主要来自 2025–2026 年，说明 BreakGate 很可能只是吃到了黄金的趋势行情，**建议调低它的资金分配**，而不是给它加单。
"反做 PF 0.05"那一项：检查镜像的止盈止损和入场所在的 K 线；镜像策略的毛 PF 应该接近基线毛 PF 的倒数。

### P1：找回实盘丢的单
1. 把 `DealLogger.mqh` 放进 `MQL5/Include/`（或者 EA 同目录），在 CT 里加入：
   ```mql5
   #include "DealLogger.mqh"
   void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &q, const MqlTradeResult &r)
     { DealLogger_OnTransaction(t); }
   ```
   在每个"有信号但没开仓"的分支里调用 `DealLogger_Skip("原因", 方向)`。原因包括点差、时段、已有持仓、保证金不足、下单报错等。
   **这项修改要先得到用户确认**，而且它只增加日志，不改变交易逻辑。
2. 让实盘跑一段时间。然后用策略测试器在**同一时间段**回测 CT，测试器会生成 `deals_..._tester.csv`。
3. 对比：
   ```bash
   python reconcile.py --live deals_CT_XAUUSD_live.csv --tester deals_CT_XAUUSD_tester.csv --magic <CT magic> --out runs/p1
   ```
   脚本会把"回测开了、实盘没开"的单按小时和星期几分布打印出来，还会输出实盘被跳过的原因统计。看到集中的空档，就去 MT5 日志里查对应时间发生了什么。

   还没加 DealLogger 的话，也可以先用 `export_mt5.py deals` 导出的历史成交，和测试器报告里的成交表手动对齐列名后再比。

### P2：CT 的瓶颈在哪里
```bash
python export_mt5.py bars --symbols XAUUSD --timeframe M15 --start 2021-01-01 --out data   # Windows 上运行
python ct_sim.py --data data/XAUUSD_M15.csv --cost XAUUSD=0.90 --max-positions 1 --out runs/ct_mp1
```
先看输出里的 `skipped_pct`，也就是"有信号但因为已有持仓而被跳过"的比例。
- **低于 15%**：瓶颈不在持仓上限，P2 到此结束。
- **比例较高**：按预登记跑 `--max-positions 2/3`，然后只看新增的那部分交易：
  ```bash
  python stats_report.py runs/ct_mp1/trades.csv --marginal runs/ct_mp3/trades.csv --pnl pnl_atr
  ```
⚠️ 先把 `ct_sim.py` 的参数和 CT v1.11 源码逐条对齐（见预登记模板第 0 节），并复现 CT 的历史回测，偏差在 ±10% 以内才能继续。

### P3：冻结参数搬到一篮子品种
```bash
python export_mt5.py bars --symbols EURUSD GBPUSD USDJPY AUDUSD US500 USTEC XAUUSD --timeframe M15 --start 2021-01-01 --out data
python export_mt5.py costs --start 2026-08-01 --out data        # 生成 data/costs_measured.csv（p90 口径）
# 先填写预登记 → 计算 sha256 → 再运行
python ct_sim.py --data "data/*_M15.csv" --cost-file data/costs_measured.csv --n-trials 24 --out runs/ct_basket
```
输出包括：每个品种的统计（含扣成本前的毛 PF）、组合统计、分年度拆解、品种之间的日收益相关性。
注意：经纪商的品种名可能和这里写的不一样（比如 US500 和 SP500），以 MT5 市场报价窗口里的名字为准。

### P4：成本审计
`export_mt5.py costs` 会读取每笔实盘成交前后的 tick，计算三项成本：成交价相对中间价的偏离、点差、每单位佣金。
**预登记时请使用 `cost_rt_p90`**。demo 账户的成交比真实账户乐观，结论以 1.5 倍成本下的结果为准。
用这个口径重跑三个"差一点"的方案：前日高低点突破、BreakGate 8 小时门控、USTEC 开盘突破。

## 已验证与未验证

- ✅ 在合成数据上跑通了完整流程：模拟器、多品种组合、边际分解、对账脚本（能正确找出人为埋下的"0–2 点漏单"）。
- ❌ `export_mt5.py` 和 `DealLogger.mqh` 没有在真实的 MT5 上运行过，因为开发环境里没有 MT5。第一次运行时请留意报错。
- ❌ `ct_sim.py` 的默认出场规则（2 倍 ATR 止损、z 回到 0、96 根 K 线时间止损）是**推测**，必须对照 CT 源码修改。
