'use client';

import { useState, useEffect } from 'react';
import './dashboard.css';

export default function Dashboard() {
  const [signalData, setSignalData] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [accountBalance, setAccountBalance] = useState('');
  const [riskPercent, setRiskPercent] = useState('');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Fetch signal data and connect to WebSocket
  useEffect(() => {
    fetchSignal();

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
  }, []);

  const fetchSignal = async () => {
    try {
      const res = await fetch('http://localhost:8000/signal?symbol=GC=F');
      const data = await res.json();
      setSignalData(data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching signal:', error);
      setLoading(false);
    }
  };

  const calculateRisk = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/risk?account_balance=${accountBalance}&risk_percent=${riskPercent}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setRiskData(data);
    } catch (error) {
      console.error('Error calculating risk:', error);
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
        <h1>🏆 XAU/USD Trading Dashboard</h1>
        <div className="header-info">
          <span className="live-indicator">🟢 LIVE</span>
          <span className="data-source-badge">📡 {signalData?.data_source || 'YAHOO'}</span>
          <span className="last-update">Updated: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="dashboard-grid">
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
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(signalData.timeframes).map(([tf, data]: [string, any]) => (
                      <tr key={tf}>
                        <td className="tf-cell">{tf}</td>
                        <td>${data.price?.toFixed(2)}</td>
                        <td className={`trend-${data.trend?.toLowerCase()}`}>{data.trend}</td>
                        <td>{data.rsi}</td>
                        <td className={`signal-${data.signal?.toLowerCase()}`}>{data.signal}</td>
                        <td className="pa-cell">{data.price_action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        {/* Risk Calculator Section */}
        <section className="card risk-card">
          <h2>💰 Risk Calculator</h2>

          <div className="risk-inputs">
            <div className="input-group">
              <label>Account Balance ($)</label>
              <input
                type="number"
                value={accountBalance}
                onChange={(e) => setAccountBalance(e.target.value)}
                placeholder="10000"
              />
            </div>

            <div className="input-group">
              <label>Risk Per Trade (%)</label>
              <input
                type="number"
                value={riskPercent}
                onChange={(e) => setRiskPercent(e.target.value)}
                placeholder="1"
                step="0.1"
              />
            </div>

            <button className="calculate-btn" onClick={calculateRisk}>
              Calculate Risk
            </button>
          </div>

          {riskData && !riskData.message && (
            <div className="risk-results">
              <div className="risk-item">
                <span className="label">Direction:</span>
                <span className={`value ${riskData.direction?.toLowerCase()}`}>
                  {riskData.direction}
                </span>
              </div>
              <div className="risk-item">
                <span className="label">Entry Price:</span>
                <span className="value">${riskData.entry_price}</span>
              </div>
              <div className="risk-item">
                <span className="label">Stop Loss:</span>
                <span className="value sl">${riskData.stop_loss}</span>
              </div>
              <div className="risk-item">
                <span className="label">Take Profit:</span>
                <span className="value tp">${riskData.take_profit}</span>
              </div>
              <div className="risk-item highlight">
                <span className="label">Position Size:</span>
                <span className="value">{riskData.position_size_lots} Lots</span>
              </div>
              <div className="risk-item">
                <span className="label">Risk Amount:</span>
                <span className="value">${riskData.risk_amount}</span>
              </div>
              <div className="risk-item">
                <span className="label">Potential Profit:</span>
                <span className="value profit">${riskData.potential_profit}</span>
              </div>
            </div>
          )}

          {riskData && riskData.message && (
            <div className="risk-message">
              <p>{riskData.message}</p>
              <p className="hint">{riskData.recommendation}</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
