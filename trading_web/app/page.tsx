'use client';

import { useState, useEffect } from 'react';
import './dashboard.css';
import './dxy.css';

export default function Dashboard() {
  const [signalData, setSignalData] = useState<any>(null);
  const [dxyData, setDxyData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [refreshingTF, setRefreshingTF] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState('GC=F'); // GC=F for Gold, BTC-USD for Bitcoin

  // Fetch signal data and connect to WebSocket
  useEffect(() => {
    fetchSignal();
    fetchDXY(); // Fetch DXY on mount

    // WebSocket Connection
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('Connected to WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'tick_update') {
          // Real-time tick from MT5 - update price display immediately
          console.log('Real-time tick:', data);
          setLastUpdate(new Date());

          // Update the price in signalData if it exists
          setSignalData((prev: any) => {
            if (!prev || !prev.timeframes) return prev;

            // Update all timeframes with the new live price
            const updatedTimeframes = { ...prev.timeframes };
            Object.keys(updatedTimeframes).forEach(tf => {
              if (updatedTimeframes[tf]) {
                updatedTimeframes[tf] = {
                  ...updatedTimeframes[tf],
                  price: data.bid // Use bid price for display
                };
              }
            });

            return {
              ...prev,
              timeframes: updatedTimeframes
            };
          });
        } else if (data.type === 'market_update') {
          // Periodic update from Yahoo or full analysis update
          console.log('Market update:', data);
          setLastUpdate(new Date());
          fetchSignal();
        }
      } catch (e) {
        console.error('Error parsing WS message:', e);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
    };

    return () => {
      ws.close();
    };
  }, [selectedSymbol]); // Re-fetch when symbol changes

  const fetchSignal = async () => {
    try {
      const res = await fetch(`http://localhost:8000/signal?symbol=${selectedSymbol}`);
      const data = await res.json();
      setSignalData(data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching signal:', error);
      setLoading(false);
    }
  };

  const refreshSingleTF = async (tf: string) => {
    setRefreshingTF(tf);
    try {
      const res = await fetch(`http://localhost:8000/signal/${tf}?symbol=${selectedSymbol}`);
      const data = await res.json();

      setSignalData((prev: any) => {
        if (!prev || !prev.timeframes) return prev;

        return {
          ...prev,
          timeframes: {
            ...prev.timeframes,
            [data.timeframe]: data.data
          }
        };
      });

      setLastUpdate(new Date());
    } catch (error) {
      console.error(`Error refreshing ${tf}:`, error);
    } finally {
      setRefreshingTF(null);
    }
  };

  const fetchDXY = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/dxy?timeframe=1d');
      const data = await res.json();
      setDxyData(data);
    } catch (error) {
      console.error('Error fetching DXY:', error);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading market data...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-top">
          <h1>🏆 Trading Dashboard</h1>
          <div className="symbol-selector">
            <button
              className={`symbol-btn ${selectedSymbol === 'GC=F' ? 'active' : ''}`}
              onClick={() => setSelectedSymbol('GC=F')}
            >
              🥇 XAU/USD
            </button>
            <button
              className={`symbol-btn ${selectedSymbol === 'BTC-USD' ? 'active' : ''}`}
              onClick={() => setSelectedSymbol('BTC-USD')}
            >
              ₿ BTC/USD
            </button>
          </div>
        </div>
        <div className="header-info">
          <span className="live-indicator">🟢 LIVE</span>
          <span className="data-source-badge">📡 {signalData?.data_source || 'YAHOO'}</span>
          <span className="last-update">Updated: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="dashboard-grid">
        {/* DXY Reference Indicator */}
        {dxyData && !dxyData.error && (
          <section className="card dxy-card">
            <h2>💵 DXY (US Dollar Index)</h2>
            <div className="dxy-summary">
              <div className="dxy-price">
                <span className="label">Price</span>
                <span className="value">{dxyData.price}</span>
              </div>
              <div className={`dxy-trend trend-${dxyData.trend?.toLowerCase()}`}>
                <span className="label">Trend</span>
                <span className="value">
                  {dxyData.trend === 'UP' && '↗ UP'}
                  {dxyData.trend === 'DOWN' && '↘ DOWN'}
                  {dxyData.trend === 'SIDEWAY' && '↔ SIDEWAY'}
                </span>
              </div>
              <div className="dxy-rsi">
                <span className="label">RSI</span>
                <span className="value">{dxyData.rsi}</span>
              </div>
            </div>
            <p className="dxy-interpretation">{dxyData.interpretation}</p>
          </section>
        )}

        {/* Signal Section */}
        <section className="card signal-card">
          <h2>📊 Trading Signals</h2>

          {signalData && (
            <>
              <div className="signal-summary">
                <div className={`signal-badge ${signalData.final_signal.toLowerCase()}`}>
                  {signalData.final_signal}
                </div>
                <div className="confluence-score">
                  <span className="score-label">Confluence Score</span>
                  <span className={`score-value grade-${signalData.confluence.grade.toLowerCase()}`}>
                    {signalData.confluence.score}/100
                  </span>
                  <span className="grade-badge">{signalData.confluence.grade}</span>
                </div>
              </div>

              <p className="recommendation">{signalData.recommendation}</p>

              <div className="confluence-factors">
                <h4>Factors:</h4>
                <ul>
                  {signalData.confluence.factors.map((factor: string, idx: number) => (
                    <li key={idx}>✓ {factor}</li>
                  ))}
                </ul>
              </div>

              <div className="timeframes-table">
                <h3>Multi-Timeframe Analysis</h3>
                <table>
                  <thead>
                    <tr>
                      <th>TF</th>
                      <th>Price</th>
                      <th>Trend</th>
                      <th>RSI</th>
                      <th>Signal</th>
                      <th>Price Action</th>
                      <th>S/R Zones</th>
                      <th>FVG Zones</th>
                      <th>OB Zones</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['1d', '4h', '1h', '30m', '15m', '5m'].map((tf) => {
                      const data = signalData.timeframes[tf];
                      if (!data) return null;
                      const isRefreshing = refreshingTF === tf;
                      return (
                        <tr key={tf}>
                          <td className="tf-cell">{tf}</td>
                          <td>${data.price?.toFixed(2)}</td>
                          <td className={`trend-${data.trend?.toLowerCase()}`}>{data.trend}</td>
                          <td>{data.rsi}</td>
                          <td className={`signal-${data.signal?.toLowerCase()}`}>{data.signal}</td>
                          <td className="pa-cell">{data.price_action}</td>
                          <td className="sr-zone-cell">{data.sr_zones || 'None'}</td>
                          <td className="fvg-zone-cell">{data.fvg_zones || 'None'}</td>
                          <td className="ob-zone-cell">{data.ob_zones || 'None'}</td>
                          <td className="action-cell">
                            <button
                              className={`refresh-btn ${isRefreshing ? 'refreshing' : ''}`}
                              onClick={() => refreshSingleTF(tf)}
                              disabled={isRefreshing}
                              title={`Refresh ${tf} analysis`}
                            >
                              {isRefreshing ? '⏳' : '🔄'}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
