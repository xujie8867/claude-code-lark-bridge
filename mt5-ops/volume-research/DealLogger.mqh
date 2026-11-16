//+------------------------------------------------------------------+
//| DealLogger.mqh  —  logging only, does not change trading logic.   |
//|                                                                  |
//| Writes every deal of this EA to a CSV with the SAME schema in     |
//| live trading and in the Strategy Tester, so reconcile.py can      |
//| compare them deal by deal (P1: why does live trade less?).        |
//|                                                                  |
//| Usage inside the EA:                                              |
//|   #include "DealLogger.mqh"                                       |
//|   void OnTradeTransaction(const MqlTradeTransaction &trans,       |
//|                           const MqlTradeRequest &req,             |
//|                           const MqlTradeResult &res)              |
//|     { DealLogger_OnTransaction(trans); /* existing code */ }      |
//| Also log REJECTED / FILTERED signals where the EA decides not to  |
//| trade:   DealLogger_Skip("spread", 1);   // reason, direction     |
//|                                                                  |
//| Output: MQL5/Files/deals_<EA>_<symbol>_<live|tester>.csv          |
//|   (tester: inside the agent's MQL5/Files folder)                  |
//+------------------------------------------------------------------+

string DealLogger__FileName()
  {
   string mode = (MQLInfoInteger(MQL_TESTER) ? "tester" : "live");
   return StringFormat("deals_%s_%s_%s.csv", MQLInfoString(MQL_PROGRAM_NAME), _Symbol, mode);
  }

void DealLogger__Write(const string line)
  {
   string fn = DealLogger__FileName();
   bool exists = FileIsExist(fn);
   int h = FileOpen(fn, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE)
      return;
   if(!exists)
      FileWriteString(h, "time,event,ticket,position_id,symbol,type,entry,volume,price,profit,commission,swap,magic,comment,bid,ask\n");
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, line + "\n");
   FileClose(h);
  }

void DealLogger_OnTransaction(const MqlTradeTransaction &trans)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   ulong d = trans.deal;
   string sym = HistoryDealGetString(d, DEAL_SYMBOL);
   DealLogger__Write(StringFormat("%s,deal,%I64u,%I64d,%s,%d,%d,%.2f,%.5f,%.2f,%.2f,%.2f,%I64d,%s,%.5f,%.5f",
      TimeToString((datetime)HistoryDealGetInteger(d, DEAL_TIME), TIME_DATE | TIME_SECONDS),
      d, HistoryDealGetInteger(d, DEAL_POSITION_ID), sym,
      (int)HistoryDealGetInteger(d, DEAL_TYPE), (int)HistoryDealGetInteger(d, DEAL_ENTRY),
      HistoryDealGetDouble(d, DEAL_VOLUME), HistoryDealGetDouble(d, DEAL_PRICE),
      HistoryDealGetDouble(d, DEAL_PROFIT), HistoryDealGetDouble(d, DEAL_COMMISSION),
      HistoryDealGetDouble(d, DEAL_SWAP), HistoryDealGetInteger(d, DEAL_MAGIC),
      HistoryDealGetString(d, DEAL_COMMENT),
      SymbolInfoDouble(sym, SYMBOL_BID), SymbolInfoDouble(sym, SYMBOL_ASK)));
  }

// Call where the EA has a valid signal but does NOT trade (filter, cap, error).
void DealLogger_Skip(const string reason, const int direction)
  {
   DealLogger__Write(StringFormat("%s,skip,0,0,%s,%d,-1,0,0,0,0,0,0,%s,%.5f,%.5f",
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), _Symbol, direction, reason,
      SymbolInfoDouble(_Symbol, SYMBOL_BID), SymbolInfoDouble(_Symbol, SYMBOL_ASK)));
  }
