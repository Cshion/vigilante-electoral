'use client';

import { useState, useEffect } from 'react';

interface LiveIndicatorProps {
  timestamp?: string;
  refreshInterval?: number; // in seconds, default 900 (15 min)
}

// Calculate next scrape time (every N minutes: :00, :15, :30, :45 for 15min interval)
function getNextScrapeTime(intervalMinutes: number = 15): Date {
  const now = new Date();
  const minutes = now.getMinutes();
  
  // Find next interval mark
  let nextMinute = Math.ceil((minutes + 1) / intervalMinutes) * intervalMinutes;
  
  const next = new Date(now);
  next.setSeconds(0);
  next.setMilliseconds(0);
  
  // Handle hour overflow
  if (nextMinute >= 60) {
    next.setHours(next.getHours() + 1);
    next.setMinutes(nextMinute - 60);
  } else {
    next.setMinutes(nextMinute);
  }
  
  return next;
}

export function LiveIndicator({ timestamp, refreshInterval = 900 }: LiveIndicatorProps) {
  const intervalMinutes = Math.floor(refreshInterval / 60);
  const [nextScrapeTime, setNextScrapeTime] = useState(() => getNextScrapeTime(intervalMinutes));
  const [timeUntilNext, setTimeUntilNext] = useState('');

  // Update next scrape time when timestamp changes
  useEffect(() => {
    setNextScrapeTime(getNextScrapeTime(intervalMinutes));
  }, [timestamp, intervalMinutes]);

  // Update countdown every second
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const diff = nextScrapeTime.getTime() - now.getTime();
      
      if (diff <= 0) {
        // Time passed, calculate new next time
        setNextScrapeTime(getNextScrapeTime(intervalMinutes));
        return;
      }
      
      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      setTimeUntilNext(`${mins}:${secs.toString().padStart(2, '0')}`);
    };
    
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, [nextScrapeTime, intervalMinutes]);

  // Format next scrape time as HH:MM
  const nextTimeFormatted = nextScrapeTime.toLocaleTimeString('es-PE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* Live Pulse */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>
        <span className="text-red-600 font-semibold hidden sm:inline">EN VIVO</span>
      </div>

      {/* Next Scrape Time */}
      <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full">
        {/* Icono de refresco con animación sutil */}
        <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span className="text-gray-600 font-mono text-xs">
          {/* En móvil solo cuenta regresiva, en desktop hora completa */}
          <span className="hidden sm:inline">Próx: {nextTimeFormatted} </span>
          <span className="text-gray-500 sm:text-gray-400">
            <span className="sm:hidden">{timeUntilNext}</span>
            <span className="hidden sm:inline">({timeUntilNext})</span>
          </span>
        </span>
      </div>
    </div>
  );
}
