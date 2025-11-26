import React from 'react';
import './FundamentalBiasWidget.css';

interface FundamentalBiasWidgetProps {
  sentimentData: any;
}

const FundamentalBiasWidget: React.FC<FundamentalBiasWidgetProps> = ({ sentimentData }) => {
  const getSentimentColor = (score: number) => {
    if (score > 0.2) return '#26a69a'; // Bullish
    if (score < -0.2) return '#ef5350'; // Bearish
    return '#fdd835'; // Neutral
  };

  const getSentimentLabel = (score: number) => {
    if (score > 0.2) return 'BULLISH';
    if (score < -0.2) return 'BEARISH';
    return 'NEUTRAL';
  };

  const score = sentimentData?.score || 0;
  const color = getSentimentColor(score);
  const label = getSentimentLabel(score);

  return (
    <div className="fundamental-bias-widget">
      <h3>📰 Fundamental Bias</h3>
      <div className="bias-content">
        <div className="bias-score" style={{ color }}>
          {label}
        </div>
        <div className="bias-meter">
          <div
            className="meter-fill"
            style={{
              width: `${((score + 1) / 2) * 100}%`,
              backgroundColor: color
            }}
          />
        </div>
        <div className="bias-details">
          <span>Score: {score.toFixed(2)}</span>
          <span>News Analyzed: {sentimentData?.news_count || 0}</span>
        </div>
      </div>
    </div>
  );
};

export default FundamentalBiasWidget;
