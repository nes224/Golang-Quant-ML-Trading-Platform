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
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `ws://localhost:8000/ws/market/${symbol}/${timeframe}`;
    console.log(`[WS] Connecting to ${wsUrl}`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`[WS] ✅ Connected: ${symbol}/${timeframe}`);
      setIsConnected(true);
      setIsLive(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastUpdate(data.timestamp);

        if (data.type === 'full_update') {
          // New candle! Update everything
          console.log(`[WS] 📊 Full update: ${data.timestamp}`);

          // Update candles
          setCandleData(prev => {
            const updated = [...prev];
            const lastCandle = updated[updated.length - 1];

            if (lastCandle && lastCandle.time === data.candle.time) {
              // Update existing candle
              updated[updated.length - 1] = data.candle;
            } else {
              // New candle
              updated.push(data.candle);

              // Limit to 500 candles in memory
              if (updated.length > 500) {
                return updated.slice(-500);
              }
            }

            return updated;
          });

          // Update signals
          setSignals(data.signals);

        } else if (data.type === 'candle_update') {
          // Just price update
          console.log(`[WS] 💹 Price update: ${data.timestamp}`);

          // Update last candle only
          setCandleData(prev => {
            if (prev.length === 0) return [data.candle];

            const updated = [...prev];
            updated[updated.length - 1] = data.candle;
            return updated;
          });
        }
      } catch (error) {
        console.error('[WS] Error parsing message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] ❌ Error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('[WS] 🔌 Disconnected');
      setIsConnected(false);
      setIsLive(false);

      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[WS] 🔄 Reconnecting...');
        connect();
      }, 3000);
    };

    wsRef.current = ws;
  }, [symbol, timeframe]);

  const reconnect = useCallback(() => {
    console.log('[WS] Manual reconnect triggered');
    connect();
  }, [connect]);

  // Fetch historical data
  const fetchMoreHistory = useCallback(async (before: string) => {
    try {
      console.log(`[HISTORY] Fetching before ${before}`);
      const response = await fetch(
        `http://localhost:8000/candlestick/${timeframe}/history?symbol=${symbol}&before=${before}&limit=100`
      );
      const data = await response.json();

      if (data.candles.length === 0) return false;

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
        pivot_points: [...data.pivot_points, ...prev.pivot_points],
        fvg_zones: [...data.fvg_zones, ...prev.fvg_zones],
        break_signals: [...data.break_signals, ...prev.break_signals],
        key_levels: [...new Set([...data.key_levels, ...prev.key_levels])]
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
      let limit = 100;
      switch (timeframe) {
        case '1m': limit = 200; break;
        case '5m': limit = 100; break;
        case '15m': limit = 75; break;
        case '30m': limit = 45; break;
        case '1h': limit = 30; break;
        case '4h': limit = 22; break;
        case '1d': limit = 15; break;
        default: limit = 100;
      }

      console.log(`[INITIAL] Fetching ${limit} candles for ${timeframe}`);
      const response = await fetch(
        `http://localhost:8000/candlestick/${timeframe}?symbol=${symbol}&limit=${limit}`
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

  // Connect on mount and when symbol/timeframe changes
  useEffect(() => {
    fetchInitialData(); // Fetch history first
    connect(); // Then start real-time updates

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect, fetchInitialData]);

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
