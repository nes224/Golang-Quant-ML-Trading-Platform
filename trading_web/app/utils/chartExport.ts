/**
 * Utility functions for exporting chart data
 */

interface CandleData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    ema_50?: number;
    ema_200?: number;
    rsi?: number;
    atr?: number;
}

interface ChartData {
    symbol: string;
    timeframe: string;
    candles: CandleData[];
    key_levels?: any[];
    pivot_points?: any[];
    fvg_zones?: any[];
    break_signals?: any[];
}

/**
 * Export chart data as CSV
 */
export function exportToCSV(data: ChartData): void {
    if (!data || !data.candles || data.candles.length === 0) {
        alert('No data to export');
        return;
    }

    // CSV Header
    const headers = [
        'Time',
        'Open',
        'High',
        'Low',
        'Close',
        'Volume',
        'EMA_50',
        'EMA_200',
        'RSI',
        'ATR'
    ];

    // CSV Rows
    const rows = data.candles.map(candle => [
        candle.time,
        candle.open.toFixed(2),
        candle.high.toFixed(2),
        candle.low.toFixed(2),
        candle.close.toFixed(2),
        candle.volume.toFixed(0),
        candle.ema_50?.toFixed(2) || '',
        candle.ema_200?.toFixed(2) || '',
        candle.rsi?.toFixed(2) || '',
        candle.atr?.toFixed(2) || ''
    ]);

    // Combine headers and rows
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');

    // Download
    downloadFile(
        csvContent,
        `${data.symbol}_${data.timeframe}_${new Date().toISOString().split('T')[0]}.csv`,
        'text/csv'
    );
}

/**
 * Export chart data as JSON
 */
export function exportToJSON(data: ChartData): void {
    if (!data || !data.candles || data.candles.length === 0) {
        alert('No data to export');
        return;
    }

    const jsonContent = JSON.stringify(data, null, 2);

    downloadFile(
        jsonContent,
        `${data.symbol}_${data.timeframe}_${new Date().toISOString().split('T')[0]}.json`,
        'application/json'
    );
}

/**
 * Helper function to trigger file download
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Format date range for display
 */
export function formatDateRange(startDate: string, endDate: string): string {
    const start = new Date(startDate);
    const end = new Date(endDate);

    const formatOptions: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };

    return `${start.toLocaleDateString('en-US', formatOptions)} - ${end.toLocaleDateString('en-US', formatOptions)}`;
}

/**
 * Calculate date range based on period
 */
export function calculateDateRange(period: string): { start: string; end: string } {
    const end = new Date();
    const start = new Date();

    switch (period) {
        case '1d':
            start.setDate(start.getDate() - 1);
            break;
        case '1w':
            start.setDate(start.getDate() - 7);
            break;
        case '1mo':
            start.setMonth(start.getMonth() - 1);
            break;
        case '3mo':
            start.setMonth(start.getMonth() - 3);
            break;
        case '6mo':
            start.setMonth(start.getMonth() - 6);
            break;
        case '1y':
            start.setFullYear(start.getFullYear() - 1);
            break;
        case 'ytd':
            start.setMonth(0, 1); // January 1st
            break;
        case 'max':
            start.setFullYear(start.getFullYear() - 5);
            break;
        default:
            start.setMonth(start.getMonth() - 1);
    }

    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
    };
}
