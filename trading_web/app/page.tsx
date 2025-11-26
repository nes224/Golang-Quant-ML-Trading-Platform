'use client';

import { useState, useEffect, useRef } from 'react';
import Navbar from '@/app/components/Navbar';
import MarketSessions from '@/app/components/MarketSessions';
import FundamentalBiasWidget from '@/app/components/FundamentalBiasWidget';
import MarketCorrelationWidget from '@/app/components/MarketCorrelationWidget';
import MultiTFIndicator from '@/app/components/MultiTFIndicator';
import { LiveIndicator } from '@/app/components/LiveIndicator';
import { useRealtimeChart } from '@/app/hooks/useRealtimeChart';
import './dashboard.css';
import './components/HistoryLoading.css';

// Declare Plotly type
declare const Plotly: any;

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState('GC=F');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [dxyData, setDxyData] = useState<any>(null);
  const [us10yData, setUs10yData] = useState<any>(null);
  const [sentimentData, setSentimentData] = useState<any>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  // Use Realtime Chart Hook
  const {
    candleData,
    signals,
    isLive,
    isConnected,
    lastUpdate,
    reconnect,
    fetchMoreHistory
  } = useRealtimeChart(selectedSymbol, selectedTimeframe);

  // Fetch DXY Data
  const fetchDXYData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/market/quote/DX-Y.NYB');
      const data = await response.json();
      setDxyData(data);
    } catch (error) {
      console.error('Error fetching DXY data:', error);
    }
  };

  // Fetch US10Y Data
  const fetchUS10YData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/market/quote/^TNX');
      const data = await response.json();
      setUs10yData(data);
    } catch (error) {
      console.error('Error fetching US10Y data:', error);
    }
  };

  // Fetch Sentiment data
  const fetchSentimentData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/news/sentiment?days=3');
      const data = await response.json();
      setSentimentData(data);
    } catch (error) {
      console.error('Error fetching sentiment data:', error);
    }
  };

  // Fetch DXY, US10Y, and Sentiment on mount and periodically
  useEffect(() => {
    fetchDXYData();
    fetchUS10YData();
    fetchSentimentData();

    const interval = setInterval(() => {
      fetchDXYData();
      fetchUS10YData();
      fetchSentimentData();
    }, 60000); // Update every 60 seconds

    return () => clearInterval(interval);
  }, []);

  // Render chart when data changes
  useEffect(() => {
    if (candleData && candleData.length > 0 && chartRef.current && typeof Plotly !== 'undefined') {
      renderChart();
    }
  }, [candleData, signals]);

  const renderChart = () => {
    if (!chartRef.current || !candleData) return;

    const candles = candleData;
    const keyLevels = signals.key_levels || [];
    const pivotPoints = signals.pivot_points || [];
    const fvgZones = signals.fvg_zones || [];
    const breakSignals = signals.break_signals || [];

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
      // Assuming level is just a number based on previous context, 
      // but if it's an object, adapt accordingly.
      // Based on hook, key_levels is number[]
      const priceLevel = typeof level === 'object' ? level.level : level;

      shapes.push({
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: priceLevel,
        y1: priceLevel,
        line: {
          color: '#2196f3',
          width: 1,
          dash: 'dash'
        }
      });
    });

    // FVG Zones as rectangles
    fvgZones.forEach((zone: any) => {
      const color = zone.type === 'bullish' ? 'rgba(0, 255, 0, 0.15)' : 'rgba(255, 0, 0, 0.15)';

      shapes.push({
        type: 'rect',
        xref: 'x',
        yref: 'y',
        x0: zone.start_time,
        x1: zone.end_time, // Or extend to current time if needed
        y0: zone.low,
        y1: zone.high,
        fillcolor: color,
        opacity: 0.6,
        layer: 'below',
        line: { width: 0 }
      });
    });

    // Calculate Y-axis range based on candles
    const prices = candles.flatMap((c: any) => [c.high, c.low]);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const padding = (maxPrice - minPrice) * 0.1; // 10% padding

    const layout = {
      title: {
        text: `${selectedSymbol} - ${selectedTimeframe} (FVG Strategy)`,
        font: { color: '#e0e3eb', size: 18, family: 'Inter, sans-serif' },
        x: 0.05,
      },
      dragmode: 'pan',
      showlegend: true,
      legend: {
        orientation: 'h',
        y: 1.05,
        x: 0.3,
        font: { color: '#848e9c' }
      },
      xaxis: {
        type: 'date',
        rangeslider: { visible: false },
        gridcolor: '#2a2e39',
        color: '#848e9c',
        linecolor: '#2a2e39',
        nticks: 10,
        tickangle: -45
      },
      yaxis: {
        gridcolor: '#2a2e39',
        color: '#848e9c',
        linecolor: '#2a2e39',
        zerolinecolor: '#2a2e39',
        side: 'right',
        range: [minPrice - padding, maxPrice + padding],
        fixedrange: false
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
      displaylogo: false,
      scrollZoom: true
    };

    Plotly.newPlot(chartRef.current, traces, layout, config);

    // Attach event listener for infinite scroll
    const chartDiv = chartRef.current as any;
    if (chartDiv) {
      chartDiv.on('plotly_relayout', handleRelayout);
    }
  };

  // Handle chart panning (Infinite Scroll)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const handleRelayout = async (event: any) => {
    // Check if x-axis range changed
    if (!event['xaxis.range[0]'] || isLoadingHistory) return;

    const startStr = event['xaxis.range[0]'];
    const startTime = new Date(startStr).getTime();

    // If panned close to the earliest data point
    if (candleData && candleData.length > 0) {
      const earliestTime = new Date(candleData[0].time).getTime();

      // If visible range start is before or close to earliest data
      // Buffer depends on timeframe, simplified here
      const buffer = 3600000 * 10;

      if (startTime <= earliestTime + buffer) {
        console.log('Load more history...');
        setIsLoadingHistory(true);

        const success = await fetchMoreHistory(candleData[0].time);

        if (success) {
          console.log('History loaded');
        }

        setIsLoadingHistory(false);
      }
    }
  };

  const handleTimeframeChange = (tf: string) => {
    setSelectedTimeframe(tf);
  };

  return (
    <div className="dashboard">
      <Navbar />

      {/* Live Indicator */}
      <LiveIndicator
        isLive={isLive}
        isConnected={isConnected}
        lastUpdate={lastUpdate}
        onReconnect={reconnect}
      />

      {/* History Loading Indicator */}
      {isLoadingHistory && (
        <div className="history-loading">
          <div className="spinner-small"></div>
          <span>Loading history...</span>
        </div>
      )}

      <header className="dashboard-header">
        <h1>📊 XAU/USD Candlestick Chart</h1>
        <div className="symbol-selector">
          <select
            value={selectedSymbol}
            onChange={(e) => {
              setSelectedSymbol(e.target.value);
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
            {/* Display first 5 key levels */}
            {signals.key_levels?.slice(0, 5).map((level: any, idx: number) => (
              <div key={idx} className="level-card support">
                <div className="level-header">
                  <span className="level-type">LEVEL</span>
                  <span className="level-strength">#{idx + 1}</span>
                </div>
                <div className="level-price">{typeof level === 'object' ? level.level : level}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Fundamental Bias Widget - Standalone */}
        <FundamentalBiasWidget sentimentData={sentimentData} />

        {/* DXY & US10Y Combined Widget */}
        <MarketCorrelationWidget dxyData={dxyData} us10yData={us10yData} />

        <div className="chart-info">
          <div className="info-card">
            <span className="info-label">Total Candles:</span>
            <span className="info-value">{candleData?.length || 0}</span>
          </div>
          <div className="info-card">
            <span className="info-label">Latest Close:</span>
            <span className="info-value">
              {candleData?.[candleData.length - 1]?.close.toFixed(2) || 'N/A'}
            </span>
          </div>
          <div className="info-card">
            <span className="info-label">Pivot Points:</span>
            <span className="info-value">{signals.pivot_points?.length || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
