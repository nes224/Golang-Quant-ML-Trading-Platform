// Fundamental Bias Widget Component (Standalone)
const FundamentalBiasWidget = ({ sentimentData }: { sentimentData: any }) => {
    if (!sentimentData || sentimentData.error) return null;

    const { score, label = 'Neutral', breakdown } = sentimentData;
    let color = '#848e9c';
    if (label && label.includes('Bullish')) color = '#0ecb81';
    if (label && label.includes('Bearish')) color = '#f6465d';
    const percentage = ((score + 10) / 20) * 100;

    return (
        <div className="dxy-widget">
            <div className="dxy-header">
                <h3>📰 Fundamental Bias (3D)</h3>
                <span className="dxy-alert-badge" style={{ backgroundColor: color }}>{label}</span>
            </div>
            <div className="dxy-content">
                <div className="dxy-price-box">
                    <span className="dxy-price" style={{ color: color }}>{score > 0 ? '+' : ''}{score}</span>
                    <span className="dxy-change">Score (-10 to +10)</span>
                </div>
                <div className="sentiment-gauge" style={{
                    height: '6px',
                    background: '#2a2e39',
                    borderRadius: '3px',
                    margin: '10px 0',
                    position: 'relative',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        height: '100%',
                        width: `${percentage}%`,
                        background: `linear-gradient(90deg, #f6465d 0%, #848e9c 50%, #0ecb81 100%)`,
                        transition: 'width 0.5s ease-out'
                    }} />
                    <div style={{
                        position: 'absolute',
                        left: '50%',
                        top: 0,
                        height: '100%',
                        width: '2px',
                        background: '#fff',
                        opacity: 0.5
                    }} />
                </div>
                <div className="dxy-correlation" style={{ justifyContent: 'space-between', fontSize: '12px' }}>
                    <span style={{ color: '#0ecb81' }}>Bull: {breakdown?.bullish || 0}</span>
                    <span style={{ color: '#848e9c' }}>Neu: {breakdown?.neutral || 0}</span>
                    <span style={{ color: '#f6465d' }}>Bear: {breakdown?.bearish || 0}</span>
                </div>
            </div>
        </div>
    );
};

// DXY & US10Y Combined Widget
const MarketCorrelationWidget = ({ dxyData, us10yData }: { dxyData: any, us10yData: any }) => {
    return (
        <div className="dxy-widget" style={{ width: '100%', maxWidth: '100%' }}>
            <div className="dxy-header">
                <h3>📊 Market Correlation Indicators</h3>
            </div>
            <div className="dxy-content">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>

                    {/* DXY Section */}
                    {dxyData && !dxyData.error && (() => {
                        const price = dxyData.price || 0;
                        const change = dxyData.change || 0;
                        const change_pct = dxyData.change_percent || 0;
                        const correlation = dxyData.correlation || 0;
                        const alert = dxyData.alert;
                        const isPositive = change >= 0;
                        const correlationColor = correlation < -0.5 ? '#0ecb81' : (correlation > 0.5 ? '#f6465d' : '#848e9c');
                        const correlationText = correlation < -0.5 ? 'Strong Inverse' : (correlation > 0.5 ? 'Positive (Risk)' : 'Weak/None');

                        return (
                            <div style={{ borderRight: '1px solid #2a2e39', paddingRight: '20px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                    <h4 style={{ margin: 0, fontSize: '14px', color: '#848e9c' }}>💵 Dollar Index (DXY)</h4>
                                    {alert && <span className="dxy-alert-badge" style={{ fontSize: '11px', padding: '2px 8px' }}>⚠️ {alert.message}</span>}
                                </div>
                                <div className="dxy-price-box">
                                    <span className="dxy-price">{price?.toFixed(3)}</span>
                                    <span className={`dxy-change ${isPositive ? 'positive' : 'negative'}`}>
                                        {isPositive ? '+' : ''}{change?.toFixed(3)} ({isPositive ? '+' : ''}{change_pct?.toFixed(2)}%)
                                    </span>
                                </div>
                                <div className="dxy-correlation">
                                    <span className="label">Gold Correlation (20):</span>
                                    <span className="value" style={{ color: correlationColor }}>
                                        {correlation?.toFixed(2)} ({correlationText})
                                    </span>
                                </div>
                            </div>
                        );
                    })()}

                    {/* US10Y Section */}
                    {us10yData && !us10yData.error && (() => {
                        const price = us10yData.price || 0;
                        const change = us10yData.change || 0;
                        const change_pct = us10yData.change_percent || 0;
                        const correlation = us10yData.correlation || 0;
                        const alert = us10yData.alert;
                        const isPositive = change >= 0;
                        const correlationColor = correlation < -0.5 ? '#0ecb81' : (correlation > 0.5 ? '#f6465d' : '#848e9c');
                        const correlationText = correlation < -0.5 ? 'Strong Inverse' : (correlation > 0.5 ? 'Positive (Risk)' : 'Weak/None');

                        return (
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                    <h4 style={{ margin: 0, fontSize: '14px', color: '#848e9c' }}>🇺🇸 US 10Y Yield</h4>
                                    {alert && <span className="dxy-alert-badge" style={{ fontSize: '11px', padding: '2px 8px' }}>⚠️ {alert.message}</span>}
                                </div>
                                <div className="dxy-price-box">
                                    <span className="dxy-price">{price?.toFixed(3)}%</span>
                                    <span className={`dxy-change ${isPositive ? 'positive' : 'negative'}`}>
                                        {isPositive ? '+' : ''}{change?.toFixed(3)} ({isPositive ? '+' : ''}{change_pct?.toFixed(2)}%)
                                    </span>
                                </div>
                                <div className="dxy-correlation">
                                    <span className="label">Gold Correlation (20):</span>
                                    <span className="value" style={{ color: correlationColor }}>
                                        {correlation?.toFixed(2)} ({correlationText})
                                    </span>
                                </div>
                            </div>
                        );
                    })()}

                </div>
            </div>
        </div>
    );
};
