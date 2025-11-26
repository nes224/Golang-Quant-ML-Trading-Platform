/**
 * LiveIndicator Component
 * 
 * Shows connection status and live mode indicator
 */

import React from 'react';
import './LiveIndicator.css';

interface LiveIndicatorProps {
    isLive: boolean;
    isConnected: boolean;
    lastUpdate: string | null;
    onReconnect?: () => void;
}

export const LiveIndicator: React.FC<LiveIndicatorProps> = ({
    isLive,
    isConnected,
    lastUpdate,
    onReconnect
}) => {
    const formatTime = (timestamp: string | null) => {
        if (!timestamp) return '--:--:--';

        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return '--:--:--';
        }
    };

    return (
        <div className="live-indicator-container">
            {isConnected && isLive ? (
                <div className="live-indicator live">
                    <span className="pulse"></span>
                    <span className="text">LIVE</span>
                    <span className="time">{formatTime(lastUpdate)}</span>
                </div>
            ) : isConnected && !isLive ? (
                <div className="live-indicator paused">
                    <span className="icon">⏸️</span>
                    <span className="text">PAUSED</span>
                    <span className="time">{formatTime(lastUpdate)}</span>
                </div>
            ) : (
                <div className="live-indicator disconnected">
                    <span className="icon">🔌</span>
                    <span className="text">DISCONNECTED</span>
                    {onReconnect && (
                        <button className="reconnect-btn" onClick={onReconnect}>
                            Reconnect
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
