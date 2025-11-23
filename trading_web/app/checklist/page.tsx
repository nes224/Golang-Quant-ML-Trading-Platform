'use client';

import { useState, useEffect, useRef } from 'react';
import Navbar from '../components/Navbar';
import './checklist.css';

// Declare Plotly type
declare const Plotly: any;

export default function ChecklistPage() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7)); // YYYY-MM
    const chartRef = useRef<HTMLDivElement>(null);

    // Load Plotly
    useEffect(() => {
        const script = document.createElement('script');
        script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
        script.async = true;
        document.body.appendChild(script);

        return () => {
            if (document.body.contains(script)) {
                document.body.removeChild(script);
            }
        };
    }, []);

    const fetchData = async () => {
        try {
            const response = await fetch(`http://localhost:8000/checklist?month=${selectedMonth}`);
            const result = await response.json();
            setData(result);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching checklist:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedMonth]);

    useEffect(() => {
        if (data && chartRef.current && typeof Plotly !== 'undefined') {
            renderChart();
        }
    }, [data]);

    const updateCount = async (item: string, change: number) => {
        try {
            const response = await fetch('http://localhost:8000/checklist/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    item,
                    change,
                    month: selectedMonth
                }),
            });

            if (response.ok) {
                const result = await response.json();
                setData(result); // Update local state with new data
            }
        } catch (error) {
            console.error('Error updating count:', error);
        }
    };

    const renderChart = () => {
        if (!chartRef.current || !data || !data.items) return;

        const items = Object.keys(data.items);
        const values = Object.values(data.items);

        // Filter out zero values for cleaner chart if needed, or keep all
        // Let's keep all but maybe sort? Or just display as is.

        const trace = {
            x: items,
            y: values,
            type: 'bar',
            marker: {
                color: '#4285f4',
            }
        };

        const layout = {
            title: {
                text: `Trading Errors - ${selectedMonth}`,
                font: { color: '#e0e3eb', size: 18 }
            },
            paper_bgcolor: '#151a21',
            plot_bgcolor: '#151a21',
            font: { family: 'Inter, sans-serif', color: '#848e9c' },
            xaxis: {
                tickangle: -45,
                automargin: true
            },
            yaxis: {
                gridcolor: '#2a2e39',
                zerolinecolor: '#2a2e39'
            },
            margin: { b: 150 } // Extra margin for rotated labels
        };

        const config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartRef.current, [trace], layout, config);
    };

    return (
        <div className="min-h-screen bg-[#0b0e11]">
            <Navbar />

            <div className="checklist-container">
                <header className="checklist-header">
                    <h1>📋 Trading Error Checklist</h1>
                    <input
                        type="month"
                        value={selectedMonth}
                        onChange={(e) => setSelectedMonth(e.target.value)}
                        className="month-selector"
                    />
                </header>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#848e9c' }}>Loading...</div>
                ) : (
                    <div className="checklist-content">
                        {/* List Section */}
                        <div className="checklist-items">
                            {Object.entries(data?.items || {}).map(([item, count]: [string, any]) => (
                                <div key={item} className="checklist-item">
                                    <span className="item-name">{item}</span>
                                    <div className="item-controls">
                                        <button
                                            className="control-btn"
                                            onClick={() => updateCount(item, -1)}
                                        >
                                            -
                                        </button>
                                        <span className={`item-count ${count > 0 ? 'positive' : ''}`}>
                                            {count}
                                        </span>
                                        <button
                                            className="control-btn"
                                            onClick={() => updateCount(item, 1)}
                                        >
                                            +
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Chart Section */}
                        <div className="chart-section">
                            <div ref={chartRef} style={{ width: '100%', height: '100%' }}></div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
