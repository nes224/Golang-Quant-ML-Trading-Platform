'use client';

import { useState } from 'react';
import './DateRangePicker.css';

interface DateRangePickerProps {
  onDateRangeChange: (startDate: string, endDate: string) => void;
  onQuickSelect: (period: string) => void;
  loading?: boolean;
}

export default function DateRangePicker({ onDateRangeChange, onQuickSelect, loading = false }: DateRangePickerProps) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);

  const quickPeriods = [
    { label: '1D', value: '1d', days: 1 },
    { label: '1W', value: '1w', days: 7 },
    { label: '1M', value: '1mo', days: 30 },
    { label: '3M', value: '3mo', days: 90 },
    { label: '6M', value: '6mo', days: 180 },
    { label: '1Y', value: '1y', days: 365 },
    { label: 'YTD', value: 'ytd', days: 0 }, // Year to date
    { label: 'ALL', value: 'max', days: 0 },
  ];

  const handleQuickSelect = (period: string, days: number) => {
    setSelectedPeriod(period);
    
    // Calculate date range
    const end = new Date();
    const start = new Date();
    
    if (period === 'ytd') {
      start.setMonth(0, 1); // January 1st of current year
    } else if (period === 'max') {
      start.setFullYear(start.getFullYear() - 5); // 5 years back
    } else {
      start.setDate(start.getDate() - days);
    }
    
    const startStr = start.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];
    
    setStartDate(startStr);
    setEndDate(endStr);
    
    onQuickSelect(period);
  };

  const handleCustomDateApply = () => {
    if (startDate && endDate) {
      setSelectedPeriod(null);
      onDateRangeChange(startDate, endDate);
    }
  };

  const handleClearDates = () => {
    setStartDate('');
    setEndDate('');
    setSelectedPeriod(null);
    onQuickSelect('live'); // Return to live mode
  };

  return (
    <div className="date-range-picker">
      <div className="quick-periods">
        {quickPeriods.map((period) => (
          <button
            key={period.value}
            className={`period-btn ${selectedPeriod === period.value ? 'active' : ''}`}
            onClick={() => handleQuickSelect(period.value, period.days)}
            disabled={loading}
          >
            {period.label}
          </button>
        ))}
      </div>

      <div className="custom-date-range">
        <div className="date-inputs">
          <div className="date-input-group">
            <label>From:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loading}
              max={endDate || new Date().toISOString().split('T')[0]}
            />
          </div>
          <div className="date-input-group">
            <label>To:</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={loading}
              min={startDate}
              max={new Date().toISOString().split('T')[0]}
            />
          </div>
        </div>
        <div className="date-actions">
          <button
            className="apply-btn"
            onClick={handleCustomDateApply}
            disabled={!startDate || !endDate || loading}
          >
            {loading ? '⏳ Loading...' : '✓ Apply'}
          </button>
          <button
            className="clear-btn"
            onClick={handleClearDates}
            disabled={loading}
          >
            🔄 Live Mode
          </button>
        </div>
      </div>
    </div>
  );
}
