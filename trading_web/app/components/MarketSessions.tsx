import React, { useState, useEffect } from 'react';

const MarketSessions: React.FC = () => {
  const [mounted, setMounted] = useState(false);
  const [currentTime, setCurrentTime] = useState<Date | null>(null);

  useEffect(() => {
    setMounted(true);
    setCurrentTime(new Date());
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted || !currentTime) return <div className="market-sessions">Loading sessions...</div>;

  // Simple session logic (UTC times)
  // Sydney: 22:00 - 07:00
  // Tokyo: 00:00 - 09:00
  // London: 08:00 - 17:00
  // New York: 13:00 - 22:00

  const getSessionStatus = (start: number, end: number) => {
    if (!currentTime) return false;
    const hour = currentTime.getUTCHours();
    if (start > end) {
      // Overnight session (e.g. Sydney)
      return (hour >= start || hour < end);
    }
    return (hour >= start && hour < end);
  };

  const sessions = [
    { name: 'Sydney', isActive: getSessionStatus(22, 7) },
    { name: 'Tokyo', isActive: getSessionStatus(0, 9) },
    { name: 'London', isActive: getSessionStatus(8, 17) },
    { name: 'New York', isActive: getSessionStatus(13, 22) },
  ];

  return (
    <div className="market-sessions">
      {sessions.map((session) => (
        <div key={session.name} className={`session-item ${session.isActive ? 'active' : ''}`}>
          <span className="status-dot"></span>
          {session.name}
        </div>
      ))}
      <div className="utc-time">
        UTC: {currentTime.toLocaleTimeString('en-US', { timeZone: 'UTC', hour12: false })}
      </div>
      <style jsx>{`
        .market-sessions {
          display: flex;
          gap: 16px;
          padding: 10px 16px;
          background: #1e222d;
          border-bottom: 1px solid #2a2e39;
          align-items: center;
          font-size: 12px;
        }
        .session-item {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #5d6575;
          font-weight: 500;
        }
        .session-item.active {
          color: #e0e3eb;
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #5d6575;
        }
        .session-item.active .status-dot {
          background: #26a69a;
          box-shadow: 0 0 6px #26a69a;
        }
        .utc-time {
          margin-left: auto;
          color: #848e9c;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
};

export default MarketSessions;
