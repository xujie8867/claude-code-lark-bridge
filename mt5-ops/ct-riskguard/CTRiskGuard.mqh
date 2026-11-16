//+------------------------------------------------------------------+
//| CTRiskGuard.mqh — in-EA risk controls for ClaudeTrendSingle (CT)  |
//|                                                                  |
//| 1) Profit cap: any CT position whose floating profit              |
//|    (POSITION_PROFIT, same field the Python script used) reaches   |
//|    InpGuardProfitCapUSD is closed at market, checked every tick.  |
//| 2) Combined position cap: open positions across ALL CT magics     |
//|    (any symbol) must stay <= InpGuardMaxPositions.                |
//|      - before opening: CTGuard_BeginOpen() refuses at the cap     |
//|        (serialised across the 4 chart instances by a terminal     |
//|        global-variable lock, so two charts cannot both take the   |
//|        last slot);                                                |
//|      - if already over (restart, manual trade with a CT magic):   |
//|        the NEWEST excess positions are closed.                    |
//|    Only positions whose magic is in InpGuardMagics are counted or |
//|    touched. v9.39 (86414/86415) and ClaudeXMBreak are never       |
//|    selected because their magics are not in the list.             |
//|                                                                  |
//| Integration in ClaudeTrendSingle.mq5 (4 edits):                   |
//|   #include "CTRiskGuard.mqh"                                      |
//|   OnInit():   if(!CTGuard_Init()) return INIT_FAILED;             |
//|               EventSetTimer(1);      // skip if EA already has one|
//|   OnTick():   CTGuard_Check();       // FIRST line                |
//|   OnTimer():  CTGuard_Check();       // covers quiet symbols      |
//|   every place that opens a position:                              |
//|       if(!CTGuard_BeginOpen()) return;   // at cap or lock busy   |
//|       ... existing OrderSend / trade.Buy / trade.Sell ...         |
//|       CTGuard_EndOpen();                 // ALWAYS, also on error |
//|                                                                  |
//| Every instance enforces both rules for all CT magics. Closes are  |
//| addressed by ticket, so several instances acting at once cannot   |
//| close more than intended (the second request just fails).         |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

input group  "=== CT RiskGuard ==="
input bool   InpGuardEnable       = true;                                   // master switch
input double InpGuardProfitCapUSD = 1200.0;                                 // per-position profit cap, 0 = off
input int    InpGuardMaxPositions = 8;                                      // combined CT positions, 0 = off
input string InpGuardMagics       = "20261107,20261110,20261111,20261112";  // CT magics, comma separated
input int    InpGuardDeviationPts = 50;                                     // max slippage for guard closes (points)

#define CTG_LOCK_NAME      "CTGuard_open_lock"
#define CTG_LOCK_STALE_SEC 10
#define CTG_RETRY_MS       2000

long   g_ctg_magics[];
CTrade g_ctg_trade;
bool   g_ctg_ready    = false;
bool   g_ctg_has_lock = false;
ulong  g_ctg_retry_ticket[];
uint   g_ctg_retry_ms[];

//--- setup -----------------------------------------------------------
bool CTGuard_Init()
  {
   string parts[];
   int n = StringSplit(InpGuardMagics, ',', parts);
   ArrayResize(g_ctg_magics, 0);
   for(int i = 0; i < n; i++)
     {
      string s = parts[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "")
         continue;
      int k = ArraySize(g_ctg_magics);
      ArrayResize(g_ctg_magics, k + 1);
      g_ctg_magics[k] = StringToInteger(s);
     }
   if(ArraySize(g_ctg_magics) == 0)
     {
      Print("CTGuard: InpGuardMagics is empty — refusing to start");
      return false;
     }
   g_ctg_trade.SetDeviationInPoints(InpGuardDeviationPts);
   g_ctg_trade.SetAsyncMode(false);
   g_ctg_ready = true;
   PrintFormat("CTGuard: enabled=%s profit_cap=%.2f max_positions=%d magics=%s (now open: %d)",
               (InpGuardEnable ? "true" : "false"), InpGuardProfitCapUSD, InpGuardMaxPositions,
               InpGuardMagics, CTGuard_Count());
   CTGuard_Check();   // handles "already over the cap after a restart"
   return true;
  }

bool CTGuard_IsCT(const long magic)
  {
   for(int i = ArraySize(g_ctg_magics) - 1; i >= 0; i--)
      if(g_ctg_magics[i] == magic)
         return true;
   return false;
  }

//--- number of open positions carrying a CT magic (all symbols) -------
int CTGuard_Count()
  {
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(CTGuard_IsCT(PositionGetInteger(POSITION_MAGIC)))
         c++;
     }
   return c;
  }

//--- close one position by ticket, retry at most every CTG_RETRY_MS ---
bool CTGuard__Close(const ulong ticket, const string why)
  {
   if(!PositionSelectByTicket(ticket))
      return true;                       // already gone (another instance closed it)
   uint now = GetTickCount();
   int slot = -1;
   for(int i = ArraySize(g_ctg_retry_ticket) - 1; i >= 0; i--)
      if(g_ctg_retry_ticket[i] == ticket)
        {
         slot = i;
         break;
        }
   if(slot >= 0 && now - g_ctg_retry_ms[slot] < CTG_RETRY_MS)
      return false;

   string sym    = PositionGetString(POSITION_SYMBOL);
   long   magic  = PositionGetInteger(POSITION_MAGIC);
   double profit = PositionGetDouble(POSITION_PROFIT);
   g_ctg_trade.SetExpertMagicNumber((ulong)magic);   // closing deal keeps the position's magic
   g_ctg_trade.SetTypeFillingBySymbol(sym);
   bool ok = g_ctg_trade.PositionClose(ticket, InpGuardDeviationPts);
   uint rc = g_ctg_trade.ResultRetcode();
   ok = ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED);
   PrintFormat("CTGuard: %s close #%I64u %s magic=%I64d profit=%.2f -> %s (retcode %u %s)",
               why, ticket, sym, magic, profit, (ok ? "OK" : "FAILED"), rc, g_ctg_trade.ResultRetcodeDescription());
   if(!ok)
     {
      if(slot < 0)
        {
         slot = ArraySize(g_ctg_retry_ticket);
         ArrayResize(g_ctg_retry_ticket, slot + 1);
         ArrayResize(g_ctg_retry_ms, slot + 1);
         g_ctg_retry_ticket[slot] = ticket;
        }
      g_ctg_retry_ms[slot] = now;
     }
   return ok;
  }

//--- call first thing in OnTick() and in OnTimer() ---------------------
void CTGuard_Check()
  {
   if(!g_ctg_ready || !InpGuardEnable)
      return;

   ulong tickets[];
   long  opened[];
   int   n = 0;

   // pass 1: profit cap + collect CT positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(!CTGuard_IsCT(PositionGetInteger(POSITION_MAGIC)))
         continue;
      long   t_msc  = PositionGetInteger(POSITION_TIME_MSC);
      double profit = PositionGetDouble(POSITION_PROFIT);
      if(InpGuardProfitCapUSD > 0 && profit >= InpGuardProfitCapUSD)
        {
         if(CTGuard__Close(tk, "PROFIT_CAP"))
            continue;                    // closed: do not count it below
        }
      ArrayResize(tickets, n + 1);
      ArrayResize(opened, n + 1);
      tickets[n] = tk;
      opened[n]  = t_msc;
      n++;
     }

   // pass 2: over the combined cap -> close the newest excess positions
   if(InpGuardMaxPositions <= 0 || n <= InpGuardMaxPositions)
      return;
   int excess = n - InpGuardMaxPositions;
   for(int e = 0; e < excess; e++)
     {
      int newest = -1;
      for(int j = 0; j < n; j++)
        {
         if(tickets[j] == 0)
            continue;
         if(newest < 0 || opened[j] > opened[newest] ||
            (opened[j] == opened[newest] && tickets[j] > tickets[newest]))
            newest = j;
        }
      if(newest < 0)
         break;
      CTGuard__Close(tickets[newest], "MAX_POSITIONS");
      tickets[newest] = 0;               // next loop picks the next-newest
     }
  }

//--- wrap every position open with BeginOpen()/EndOpen() ---------------
// Returns false when the combined cap is reached or another chart is in the
// middle of opening. In both cases: do not open now; the signal can retry on
// the next tick if the EA normally would.
bool CTGuard_BeginOpen()
  {
   if(!g_ctg_ready || !InpGuardEnable || InpGuardMaxPositions <= 0)
      return true;

   double now = (double)TimeLocal();
   if(!GlobalVariableCheck(CTG_LOCK_NAME))
      GlobalVariableSet(CTG_LOCK_NAME, 0.0);
   bool got = GlobalVariableSetOnCondition(CTG_LOCK_NAME, now, 0.0);
   if(!got)
     {
      double held = GlobalVariableGet(CTG_LOCK_NAME);
      if(held > 0.0 && now - held > CTG_LOCK_STALE_SEC)        // holder crashed: take over
         got = GlobalVariableSetOnCondition(CTG_LOCK_NAME, now, held);
     }
   if(!got)
      return false;
   g_ctg_has_lock = true;

   int open_now = CTGuard_Count();
   if(open_now >= InpGuardMaxPositions)
     {
      PrintFormat("CTGuard: open refused on %s — %d CT positions open, cap %d",
                  _Symbol, open_now, InpGuardMaxPositions);
      CTGuard_EndOpen();
      return false;
     }
   return true;
  }

void CTGuard_EndOpen()
  {
   if(!g_ctg_has_lock)
      return;
   GlobalVariableSet(CTG_LOCK_NAME, 0.0);
   g_ctg_has_lock = false;
  }

// Call from OnDeinit() so a removed EA never leaves the lock held.
void CTGuard_Deinit()
  {
   CTGuard_EndOpen();
  }
