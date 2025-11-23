'use client';

import { useState, useEffect } from 'react';

// Market Hours Component
export function MarketHours() {
    const [currentTime, setCurrentTime] = useState(new Date());

    const markets = [
        { name: 'Sydney', flag: '🇦🇺', code: 'AUD', open: 5, close: 13, class: 'market-sydney' },
        { name: 'Tokyo', flag: '🇯🇵', code: 'JPY', open: 6, close: 14, class: 'market-tokyo' },
        { name: 'Shanghai', flag: '🇨🇳', code: 'CNY', open: 8, close: 15, class: 'market-shanghai' },
        { name: 'Switzerland', flag: '🇨🇭', code: 'CHF', open: 14, close: 22, class: 'market-switzerland' },
        { name: 'Europe', flag: '🇪🇺', code: 'EUR', open: 14, close: 22, class: 'market-europe' },
        { name: 'London', flag: '🇬🇧', code: 'GBP', open: 15, close: 23, class: 'market-london' },
        { name: 'New York', flag: '🇺🇸', code: 'USD', open: 20, close: 4, class: 'market-newyork' },
        { name: 'Canada', flag: '🇨🇦', code: 'CAD', open: 20, close: 4, class: 'market-canada' },
    ];

    // Update time every 1 minute (60000ms)
    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentTime(new Date());
        }, 60000); // Update every 1 minute

        return () => clearInterval(interval);
    }, []);

    // Get current hour in GMT+7 (Bangkok time)
    const currentHour = currentTime.getHours();

    const isMarketOpen = (open: number, close: number) => {
        if (open < close) {
            return currentHour >= open && currentHour < close;
        } else {
            // Market crosses midnight
            return currentHour >= open || currentHour < close;
        }
    };

    const getBarSegments = (open: number, close: number) => {
        const totalHours = 24;
        const segments = [];

        if (open < close) {
            // Normal case: single segment
            segments.push({
                left: (open / totalHours) * 100,
                width: ((close - open) / totalHours) * 100
            });
        } else {
            // Market crosses midnight: two segments
            // First segment: from open to end of day (24:00)
            segments.push({
                left: (open / totalHours) * 100,
                width: ((totalHours - open) / totalHours) * 100
            });
            // Second segment: from start of day (0:00) to close
            segments.push({
                left: 0,
                width: (close / totalHours) * 100
            });
        }

        return segments;
    };

    const getCurrentTimePosition = () => {
        return (currentHour / 24) * 100;
    };

    return (
        <div className="market-hours-section">
            <h3>🌍 Global Market Hours (GMT+7)</h3>

            <div className="market-hours-grid">
                {markets.map((market) => {
                    const isOpen = isMarketOpen(market.open, market.close);
                    const barSegments = getBarSegments(market.open, market.close);

                    return (
                        <div key={market.code} className={`market-row ${market.class} ${isOpen ? 'active' : ''}`}>
                            <div className="market-name">
                                <span className="market-flag">{market.flag}</span>
                                <span>{market.name}</span>
                                <span className="market-code">({market.code})</span>
                            </div>

                            <div className="market-timeline">
                                {barSegments.map((segment, index) => (
                                    <div
                                        key={index}
                                        className="market-bar"
                                        style={{
                                            left: `${segment.left}%`,
                                            width: `${segment.width}%`
                                        }}
                                    />
                                ))}
                                <div className="current-time-line" style={{ left: `${getCurrentTimePosition()}%` }}></div>
                            </div>

                            <div className={`market-status ${isOpen ? 'open' : 'closed'}`}>
                                {isOpen ? 'OPEN' : 'CLOSED'}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="time-labels">
                <div></div>
                <div className="time-labels-hours">
                    {Array.from({ length: 25 }, (_, i) => (
                        <div key={i} className="time-label">
                            {i}
                        </div>
                    ))}
                </div>
                <div></div>
            </div>
        </div>
    );
}
