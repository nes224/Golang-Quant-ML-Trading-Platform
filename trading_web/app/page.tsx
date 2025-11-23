'use client';

import { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import MultiTFIndicator from './components/MultiTFIndicator';
import './dashboard.css';

// Declare Plotly type
declare const Plotly: any;

// Market Sessions Component
const MarketSessions = () => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const sessions = [
    { name: 'Sydney (AUD)', start: 5, end: 14, color: '#4caf50' }, // 05:00 - 14:00
    { name: 'Tokyo (JPY)', start: 6, end: 15, color: '#2196f3' },   // 06:00 - 15:00
    { name: 'China (CNY)', start: 8, end: 16, color: '#f44336' },   // 08:00 - 16:00
    { name: 'Swiss (CHF)', start: 13, end: 21, color: '#e91e63' },  // 13:00 - 21:00
    { name: 'Europe (EUR)', start: 14, end: 23, color: '#9c27b0' }, // 14:00 - 23:00
    { name: 'London (GBP)', start: 15, end: 24, color: '#ff9800' }, // 15:00 - 00:00 (24)
    { name: 'New York (USD)', start: 19, end: 28, color: '#ff5722' }, // 19:00 - 04:00 (+1 day)
    { name: 'Canada (CAD)', start: 19, end: 28, color: '#795548' },   // 19:00 - 04:00 (+1 day)
  ];

  const currentHour = currentTime.getHours() + currentTime.getMinutes() / 60;

  return (
    <div className="market-sessions">
      <h3>🕒 Market Sessions (UTC+7)</h3>
      <div className="sessions-grid">
        {/* Time Header */}
        <div className="session-row header">
          <div className="session-label">Time</div>
          <div className="session-timeline">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="time-marker">{i}</div>
            ))}
          </div>
        </div>

        {/* Sessions */}
        {sessions.map((session) => {
          const start = session.start;
          const end = session.end;

          // Calculate first segment (up to midnight)
          // If end > 24, the first bar goes from start to 24.
          // If end <= 24, the bar goes from start to end.
          const firstSegmentDuration = end > 24 ? (24 - start) : (end - start);

          // Calculate second segment (after midnight, if any)
          const secondSegmentDuration = end > 24 ? (end - 24) : 0;

          // Check if current time falls within the session
          // Case 1: Standard session (e.g., 08:00 - 16:00) -> start <= now < end
          // Case 2: Crossing midnight (e.g., 19:00 - 04:00) -> (start <= now < 24) OR (0 <= now < end-24)
          const isActive = end > 24
            ? (currentHour >= start || currentHour < (end - 24))
            : (currentHour >= start && currentHour < end);

          return (
            <div key={session.name} className="session-row">
              <div className="session-label">{session.name}</div>
              <div className="session-timeline">
                {/* First Segment */}
                <div
                  className="session-bar"
                  style={{
                    left: `${(start / 24) * 100}%`,
                    width: `${(firstSegmentDuration / 24) * 100}%`,
                    backgroundColor: session.color,
                    opacity: isActive ? 1 : 0.3
                  }}
                />

                {/* Second Segment (Wrap around) */}
                {secondSegmentDuration > 0 && (
                  <div
                    className="session-bar wrap"
                    style={{
                      left: `0%`,
                      width: `${(secondSegmentDuration / 24) * 100}%`,
                      backgroundColor: session.color,
                      opacity: isActive ? 1 : 0.3
                    }}
                  />
                )}

              </div>
            </div>
          );
        })}

        {/* Current Time Indicator */}
        <div
          className="current-time-line"
          style={{ left: `calc(120px + (100% - 120px) * ${currentHour / 24})` }}
        ></div>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const [candleData, setCandleData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [selectedSymbol, setSelectedSymbol] = useState('GC=F');
  const chartRef = useRef<HTMLDivElement>(null);

  // Load Plotly from CDN
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  // Fetch candlestick data
  const fetchCandleData = async (timeframe: string = selectedTimeframe) => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/candlestick/${timeframe}?symbol=${selectedSymbol}&limit=200`
      );
      const data = await response.json();
      setCandleData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching candle data:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandleData();

    // WebSocket Connection for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('Connected to WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'candle_update' && data.timeframe === selectedTimeframe) {
          console.log('Candle update:', data);
          setCandleData(data);
        }
      } catch (error) {
        console.error('WebSocket error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.close();
    };
  }, [selectedTimeframe, selectedSymbol]);

  // Render chart when data changes
  useEffect(() => {
    if (candleData && candleData.candles && chartRef.current && typeof Plotly !== 'undefined') {
      renderChart();
    }
  }, [candleData]);

  const renderChart = () => {
    if (!chartRef.current || !candleData) return;

    const candles = candleData.candles;
    const keyLevels = candleData.key_levels || [];
    const pivotPoints = candleData.pivot_points || [];
    const fvgZones = candleData.fvg_zones || [];
    const breakSignals = candleData.break_signals || [];

    console.log('Rendering chart with:', {
      candles: candles.length,
      keyLevels: keyLevels.length,
      pivotPoints: pivotPoints.length,
      fvgZones: fvgZones.length,
      breakSignals: breakSignals.length,
      pivotSample: pivotPoints.slice(0, 3),
      candlePriceRange: candles.length > 0 ? {
        min: Math.min(...candles.map((c: any) => c.low)),
        max: Math.max(...candles.map((c: any) => c.high))
      } : null
    });

    // Prepare data for Plotly
    const x = candles.map((c: any) => c.time);
    const open = candles.map((c: any) => c.open);
    const high = candles.map((c: any) => c.high);
    const low = candles.map((c: any) => c.low);
    const close = candles.map((c: any) => c.close);

    // Candlestick trace
    const trace1 = {
      x: x,
      open: open,
      high: high,
      low: low,
      close: close,
      type: 'candlestick',
      name: 'OHLC',
      increasing: { line: { color: '#26a69a' } },
      decreasing: { line: { color: '#ef5350' } },
      xaxis: 'x',
      yaxis: 'y'
    };

    // Pivot Points
    const pivotX = pivotPoints.map((p: any) => p.time);
    const pivotY = pivotPoints.map((p: any) => p.price);
    const trace2 = {
      x: pivotX,
      y: pivotY,
      type: 'scatter',
      mode: 'markers',
      name: 'Pivot Points',
      marker: {
        size: 10,
        color: '#ff00ff',  // Bright magenta
        symbol: 'circle',
        line: { color: '#ffffff', width: 1 }
      },
      xaxis: 'x',
      yaxis: 'y'
    };

    // Break Signals (BUY/SELL)
    const buySignals = breakSignals.filter((s: any) => s.type === 'buy');
    const sellSignals = breakSignals.filter((s: any) => s.type === 'sell');

    const trace3 = {
      x: buySignals.map((s: any) => s.time),
      y: buySignals.map((s: any) => s.price),
      type: 'scatter',
      mode: 'markers',
      name: 'BUY Signal',
      marker: { size: 12, color: '#00ff00', symbol: 'triangle-up' },
      xaxis: 'x',
      yaxis: 'y'
    };

    const trace4 = {
      x: sellSignals.map((s: any) => s.time),
      y: sellSignals.map((s: any) => s.price),
      type: 'scatter',
      mode: 'markers',
      name: 'SELL Signal',
      marker: { size: 12, color: '#ff0000', symbol: 'triangle-down' },
      xaxis: 'x',
      yaxis: 'y'
    };

    const traces: any[] = [trace1, trace2, trace3, trace4];

    // Add shapes (Key Levels + FVG Zones)
    const shapes: any[] = [];

    // Key Levels as horizontal lines
    keyLevels.forEach((level: any) => {
      const color = level.type === 'support' ? '#26a69a' : '#ef5350';
      shapes.push({
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: level.level,
        y1: level.level,
        line: {
          color: color,
          width: 2,
          dash: 'dash'
        }
      });
    });

    // FVG Zones as rectangles
    fvgZones.forEach((zone: any) => {
      const color = zone.type === 'bullish' ? 'rgba(0, 255, 0, 0.15)' : 'rgba(255, 0, 0, 0.15)';
      const timeIndex = x.indexOf(zone.time);
      if (timeIndex >= 0) {
        shapes.push({
          type: 'rect',
          xref: 'x',
          yref: 'y',
          x0: x[timeIndex],
          x1: x[Math.min(timeIndex + 30, x.length - 1)],
          y0: zone.start,
          y1: zone.end,
          fillcolor: color,
          opacity: 0.6,
          layer: 'below',
          line: { width: 0 }
        });
      }
    });

    const layout = {
      title: {
        text: `${candleData.symbol} - ${candleData.timeframe} (FVG Strategy)`,
        font: { color: '#e0e3eb', size: 18, family: 'Inter, sans-serif' },
        x: 0.05,
      },
      dragmode: 'zoom',
      showlegend: true,
      legend: {
        orientation: 'h',
        y: 1.05,
        x: 0.3,
        font: { color: '#848e9c' }
      },
      xaxis: {
        rangeslider: { visible: false },
        gridcolor: '#2a2e39',
        color: '#848e9c',
        linecolor: '#2a2e39'
      },
      yaxis: {
        gridcolor: '#2a2e39',
        color: '#848e9c',
        linecolor: '#2a2e39',
        zerolinecolor: '#2a2e39',
        side: 'right'
      },
      shapes: shapes,
      plot_bgcolor: '#151a21',
      paper_bgcolor: '#151a21',
      font: { family: 'Inter, sans-serif', color: '#e0e3eb' },
      margin: { t: 60, b: 40, l: 60, r: 40 },
      hovermode: 'x unified'
    };

    const config = {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      displaylogo: false
    };

    Plotly.newPlot(chartRef.current, traces, layout, config);
  };

  const handleTimeframeChange = (tf: string) => {
    setSelectedTimeframe(tf);
    fetchCandleData(tf);
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading chart data...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Navbar />
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>📊 XAU/USD Candlestick Chart</h1>
          <div className="symbol-selector">
            <select
              value={selectedSymbol}
              onChange={(e) => {
                setSelectedSymbol(e.target.value);
                fetchCandleData();
              }}
              className="symbol-select"
            >
              <option value="GC=F">Gold Futures (GC=F)</option>
              <option value="XAUUSD=X">Spot Gold (XAUUSD=X)</option>
            </select>
          </div>
        </header>

        <MarketSessions />

        <div className="timeframe-selector" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['1m', '5m', '15m', '30m', '1h', '4h', '1d'].map((tf) => (
              <button
                key={tf}
                className={`tf-btn ${selectedTimeframe === tf ? 'active' : ''}`}
                onClick={() => handleTimeframeChange(tf)}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
          <MultiTFIndicator symbol={selectedSymbol} />
        </div>

        <div className="chart-container" style={{ position: 'relative' }}>
          <div ref={chartRef} className="plotly-chart"></div>

          <div className="key-levels-section">
            <h3>🎯 Key Support/Resistance Levels</h3>
            <div className="key-levels-grid">
              {candleData?.key_levels?.slice(0, 5).map((level: any, idx: number) => (
                <div key={idx} className={`level-card ${level.type}`}>
                  <div className="level-header">
                    <span className="level-type">{level.type ? level.type.toUpperCase() : 'N/A'}</span>
                    <span className="level-strength">Strength: {level.strength || 0}</span>
                  </div>
                  <div className="level-price">{level.level || 'N/A'}</div>
                  <div className="level-details">
                    <span>High Touches: {level.high_touches || 0}</span>
                    <span>Low Touches: {level.low_touches || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="chart-info">
            <div className="info-card">
              <span className="info-label">Total Candles:</span>
              <span className="info-value">{candleData?.total || 0}</span>
            </div>
            <div className="info-card">
              <span className="info-label">Latest Close:</span>
              <span className="info-value">
                {candleData?.candles?.[candleData.candles.length - 1]?.close.toFixed(2) || 'N/A'}
              </span>
            </div>
            <div className="info-card">
              <span className="info-label">RSI:</span>
              <span className="info-value">
                {candleData?.candles?.[candleData.candles.length - 1]?.rsi?.toFixed(2) || 'N/A'}
              </span>
            </div>
            <div className="info-card">
              <span className="info-label">Pivot Points:</span>
              <span className="info-value">{candleData?.pivot_points?.length || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
