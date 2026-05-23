'use client';

// STATIC MODE: Show "Final" badge instead of live countdown

interface LiveIndicatorProps {
  timestamp?: string;
  refreshInterval?: number; // Unused in static mode
}

export function LiveIndicator({ timestamp }: LiveIndicatorProps) {
  // Format the final data timestamp
  const formattedDate = timestamp 
    ? new Date(timestamp).toLocaleDateString('es-PE', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      })
    : '';

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* Final Badge */}
      <div className="flex items-center gap-1.5 px-2 py-1 bg-green-100 rounded-full">
        <span className="relative flex h-2 w-2">
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </span>
        <span className="text-green-700 font-semibold">FINAL</span>
      </div>

      {/* Data timestamp */}
      {formattedDate && (
        <div className="hidden sm:flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full">
          <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-gray-600 text-xs">{formattedDate}</span>
        </div>
      )}
    </div>
  );
}
