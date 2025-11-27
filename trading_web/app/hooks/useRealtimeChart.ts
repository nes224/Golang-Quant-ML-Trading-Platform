/**
 * useRealtimeChart Hook
 * 
 * Manages WebSocket connection for real-time chart updates
 * with incremental signal updates and historical data fetching.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Signals {
  pivot_points: Array<{
    time: string;
    price: number;
    type: string;
  }>;
  fvg_zones: Array<{
    start_time: string;
    end_time: string;
    low: number;
    high: number;
    type: string;
  }>;
  break_signals: Array<{
    time: string;
    price: number;
    type: string;
  }>;
  key_levels: number[];
}

interface RealtimeChartData {
  candleData: Candle[];
  signals: Signals;
  isLive: boolean;
  isConnected: boolean;
  lastUpdate: string | null;
  reconnect: () => void;
  fetchMoreHistory: (before: string) => Promise<boolean>;
}

export const useRealtimeChart = (
  symbol: string,
  timeframe: string
): RealtimeChartData => {
  const [candleData, setCandleData] = useState<Candle[]>([]);
  const [signals, setSignals] = useState<Signals>({
    pivot_points: [],
    fvg_zones: [],
    break_signals: [],
    key_levels: []
  });
  const [isLive, setIsLive] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    // No WebSocket - just use polling
    console.log(`[POLLING] Starting auto-refresh for ${symbol}/${timeframe}`);
    setIsConnected(true);
    setIsLive(true);
  }, [symbol, timeframe]);

  const reconnect = useCallback(() => {
    console.log('[POLLING] Manual refresh triggered');
    fetchInitialData();
  }, []);

  // Fetch historical data
  const fetchMoreHistory = useCallback(async (before: string) => {
    try {
      console.log(`[HISTORY] Fetching before ${before}`);
      
      // Calculate date range (fetch 100 candles before the given time)
      const beforeDate = new Date(before);
      const endDate = beforeDate.toISOString().split('T')[0]; // YYYY-MM-DD
      
      // Calculate start date based on timeframe
      let daysBack = 7; // default
      switch (timeframe) {
        case '1m': daysBack = 1; break;
        case '5m': daysBack = 2; break;
        case '15m': daysBack = 3; break;
        case '30m': daysBack = 5; break;
        case '1h': daysBack = 7; break;
        case '4h': daysBack = 30; break;
        case '1d': daysBack = 100; break;
      }
      
      const startDate = new Date(beforeDate);
      startDate.setDate(startDate.getDate() - daysBack);
      const startStr = startDate.toISOString().split('T')[0];
      
      const response = await fetch(
        `http://localhost:8000/api/v1/candlestick/${timeframe}?symbol=${symbol}&start=${startStr}&end=${endDate}&limit=100`
      );
      
      if (!response.ok) {
        console.error(`[HISTORY] API error: ${response.status}`);
        return false;
      }
      
      const data = await response.json();

      if (!data || !data.candles || data.candles.length === 0) {
        console.log('[HISTORY] No more data available');
        return false;
      }

      // Merge candles (prepend)
      setCandleData(prev => {
        // Filter out any duplicates based on time
        const newCandles = data.candles.filter((c: Candle) =>
          !prev.some(p => p.time === c.time)
        );
        return [...newCandles, ...prev];
      });

      // Merge signals
      setSignals(prev => ({
        pivot_points: [...(data.pivot_points || []), ...prev.pivot_points],
        fvg_zones: [...(data.fvg_zones || []), ...prev.fvg_zones],
        break_signals: [...(data.break_signals || []), ...prev.break_signals],
        key_levels: [...new Set([...(data.key_levels || []), ...prev.key_levels])]
      }));

      return true;
    } catch (error) {
      console.error('[HISTORY] Error fetching history:', error);
      return false;
    }
  }, [symbol, timeframe]);

  // Fetch initial data
  const fetchInitialData = useCallback(async () => {
    try {
      // Determine limit based on timeframe
      // Determine limit based on timeframe - User requested ~200 candles
      let limit = 200;
      
      // We can still adjust slightly if needed, but keeping it consistent is better
      // switch (timeframe) {
      //   case '1m': limit = 200; break;
      //   default: limit = 200;
      // }

      console.log(`[INITIAL] Fetching ${limit} candles for ${timeframe}`);
      const response = await fetch(
        `http://localhost:8000/api/v1/candlestick/${timeframe}?symbol=${symbol}&limit=${limit}`
      );
      const data = await response.json();

      if (data.candles) {
        setCandleData(data.candles);
        setSignals({
          pivot_points: data.pivot_points || [],
          fvg_zones: data.fvg_zones || [],
          break_signals: data.break_signals || [],
          key_levels: data.key_levels || []
        });
        setLastUpdate(new Date().toISOString());
      }
    } catch (error) {
      console.error('[INITIAL] Error fetching initial data:', error);
    }
  }, [symbol, timeframe]);

  // Polling: Fetch data on mount and every 10 seconds
  useEffect(() => {
    fetchInitialData(); // Initial fetch
    connect(); // Set connected state

    // Auto-refresh every 10 seconds
    const interval = setInterval(() => {
      console.log('[POLLING] Auto-refresh...');
      fetchInitialData();
    }, 10000);

    // Cleanup on unmount
    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [symbol, timeframe, fetchInitialData, connect]);

  return {
    candleData,
    signals,
    isLive,
    isConnected,
    lastUpdate,
    reconnect,
    fetchMoreHistory
  };
};
