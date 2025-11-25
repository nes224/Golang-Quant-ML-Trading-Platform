'use client';

import { useState } from 'react';
import './ChartControls.css';

interface ChartControlsProps {
    onNavigate: (direction: 'prev' | 'next') => void;
    onExport: (format: 'csv' | 'json') => void;
    onZoomReset: () => void;
    canNavigatePrev: boolean;
    canNavigateNext: boolean;
    loading?: boolean;
    currentRange?: string;
}

export default function ChartControls({
    onNavigate,
    onExport,
    onZoomReset,
    canNavigatePrev,
    canNavigateNext,
    loading = false,
    currentRange
}: ChartControlsProps) {
    const [showExportMenu, setShowExportMenu] = useState(false);

    const handleExport = (format: 'csv' | 'json') => {
        onExport(format);
        setShowExportMenu(false);
    };

    return (
        <div className="chart-controls">
            <div className="control-group navigation">
                <button
                    className="control-btn"
                    onClick={() => onNavigate('prev')}
                    disabled={!canNavigatePrev || loading}
                    title="Previous Period"
                >
                    ◀ Previous
                </button>
                <button
                    className="control-btn"
                    onClick={() => onNavigate('next')}
                    disabled={!canNavigateNext || loading}
                    title="Next Period"
                >
                    Next ▶
                </button>
            </div>

            {currentRange && (
                <div className="current-range">
                    <span className="range-label">Viewing:</span>
                    <span className="range-value">{currentRange}</span>
                </div>
            )}

            <div className="control-group actions">
                <button
                    className="control-btn zoom-reset"
                    onClick={onZoomReset}
                    disabled={loading}
                    title="Reset Zoom"
                >
                    🔍 Reset Zoom
                </button>

                <div className="export-dropdown">
                    <button
                        className="control-btn export-btn"
                        onClick={() => setShowExportMenu(!showExportMenu)}
                        disabled={loading}
                        title="Export Data"
                    >
                        📥 Export
                    </button>
                    {showExportMenu && (
                        <div className="export-menu">
                            <button
                                className="export-option"
                                onClick={() => handleExport('csv')}
                            >
                                📊 Export as CSV
                            </button>
                            <button
                                className="export-option"
                                onClick={() => handleExport('json')}
                            >
                                📄 Export as JSON
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
