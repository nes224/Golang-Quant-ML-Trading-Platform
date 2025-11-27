'use client';

import { useState, useEffect } from 'react';
import './MultiTFIndicator.css';

interface TrendData {
    trend: string;
    strength: number;
    color: string;
}

interface MultiTFIndicatorProps {
    symbol: string;
}

export default function MultiTFIndicator({ symbol }: MultiTFIndicatorProps) {
    const [trends, setTrends] = useState<Record<string, TrendData>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchTrends();
        // Refresh every 5 minutes
        const interval = setInterval(fetchTrends, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [symbol]);

    const fetchTrends = async () => {
        try {
            const response = await fetch(`http://localhost:8000/api/v1/multi-tf-trend?symbol=${symbol}`);
            const data = await response.json();
            setTrends(data);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching multi-TF trends:', error);
            setLoading(false);
        }
    };

    const getTrendIcon = (trend: string) => {
        if (trend === 'UPTREND') return '↗';
        if (trend === 'DOWNTREND') return '↘';
        if (trend === 'SIDEWAYS') return '→';
        return '?';
    };

    const timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];

    return (
        <div className="multi-tf-indicator-inline">
            <span className="mtf-label">MTF Trend:</span>
            {!loading && (
                <div className="mtf-trends">
                    {timeframes.map((tf) => {
                        const trendData = trends[tf];
                        if (!trendData) return null;

                        return (
                            <div key={tf} className="mtf-item" title={`${tf.toUpperCase()}: ${trendData.trend} (${trendData.strength})`}>
                                <span className="mtf-tf">{tf.toUpperCase()}</span>
                                <span
                                    className="mtf-arrow"
                                    style={{ color: trendData.color }}
                                >
                                    {getTrendIcon(trendData.trend)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
            {loading && <span className="mtf-loading">Loading...</span>}
        </div>
    );
}
