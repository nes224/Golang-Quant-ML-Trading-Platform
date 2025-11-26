import React from 'react';
import './MarketCorrelationWidget.css';

interface MarketCorrelationWidgetProps {
  dxyData: any;
  us10yData: any;
}

const MarketCorrelationWidget: React.FC<MarketCorrelationWidgetProps> = ({ dxyData, us10yData }) => {
  const getChangeColor = (change: number) => {
    if (!change) return '#848e9c';
    return change >= 0 ? '#26a69a' : '#ef5350';
  };

  return (
    <div className="market-correlation-widget">
      <h3>🔗 Market Correlation</h3>
      <div className="correlation-grid">
        {/* DXY Card */}
        <div className="correlation-card">
          <div className="card-header">
            <span className="symbol">DXY</span>
            <span className="name">US Dollar Index</span>
          </div>
          <div className="card-body">
            <div className="price">{dxyData?.price?.toFixed(2) || '---'}</div>
            <div className="change" style={{ color: getChangeColor(dxyData?.change) }}>
              {dxyData?.change > 0 ? '+' : ''}{dxyData?.change?.toFixed(2) || '0.00'}%
            </div>
          </div>
        </div>

        {/* US10Y Card */}
        <div className="correlation-card">
          <div className="card-header">
            <span className="symbol">US10Y</span>
            <span className="name">US 10Y Yield</span>
          </div>
          <div className="card-body">
            <div className="price">{us10yData?.price?.toFixed(2) || '---'}</div>
            <div className="change" style={{ color: getChangeColor(us10yData?.change) }}>
              {us10yData?.change > 0 ? '+' : ''}{us10yData?.change?.toFixed(2) || '0.00'}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketCorrelationWidget;
