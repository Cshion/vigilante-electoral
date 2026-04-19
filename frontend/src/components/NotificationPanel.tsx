'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useNotifications } from '@/hooks/useResults';
import { Notification } from '@/lib/types';
import { formatActas } from '@/lib/utils';

interface NotificationPanelProps {
  onRegionSelect?: (regionCode: string) => void;
}

const ITEMS_PER_PAGE = 15;

export function NotificationPanel({ onRegionSelect }: NotificationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const lastRefreshRef = useRef<number>(0);
  // Fetch up to 100 notifications from the last week (168 hours)
  const { notifications, count, isLoading, isError, refresh } = useNotifications(100, 168);
  
  const totalPages = Math.ceil(notifications.length / ITEMS_PER_PAGE);
  const paginatedNotifications = notifications.slice(
    currentPage * ITEMS_PER_PAGE,
    (currentPage + 1) * ITEMS_PER_PAGE
  );

  // Refresh on panel open, but throttle to max once per minute
  const handleToggle = useCallback(() => {
    const now = Date.now();
    if (!isExpanded && now - lastRefreshRef.current > 60000) {
      refresh();
      lastRefreshRef.current = now;
    }
    setIsExpanded(!isExpanded);
  }, [isExpanded, refresh]);

  const handleNotificationClick = useCallback((notification: Notification) => {
    if (onRegionSelect) {
      onRegionSelect(notification.region_code);
    }
    setIsExpanded(false);
  }, [onRegionSelect]);

  // Close panel on Escape key (accessibility)
  useEffect(() => {
    if (!isExpanded) return;
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsExpanded(false);
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isExpanded]);

  // Format time ago
  const timeAgo = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'ahora';
    if (diffMins < 60) return `${diffMins}m`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h`;
    return `${Math.floor(diffHours / 24)}d`;
  };

  // Get region emoji
  const getRegionEmoji = (regionCode: string): string => {
    if (regionCode === 'EXTRANJERO') return '🌍';
    return '📍';
  };

  return (
    <div className="relative">
      {/* Notification Bell/Toggle */}
      <button
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-label={`Notificaciones: ${count} cambios`}
        className={`relative flex items-center gap-1.5 px-3 py-2 rounded-xl transition-all ${
          isExpanded
            ? 'bg-amber-100 text-amber-800 border-2 border-amber-300'
            : 'bg-white/80 hover:bg-amber-50 text-gray-700 border border-gray-200 hover:border-amber-200'
        }`}
      >
        <span className="text-lg">🔔</span>
        <span className="text-sm font-medium hidden sm:inline">Cambios</span>
        {count > 0 && (
          <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center min-w-[20px] h-5 px-1 bg-amber-500 text-white text-xs font-bold rounded-full">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {/* Expanded Panel */}
      {isExpanded && (
        <>
          {/* Backdrop - más oscuro en móvil */}
          <div 
            className="fixed inset-0 z-40 bg-black/20 sm:bg-transparent" 
            onClick={() => setIsExpanded(false)}
          />
          
          {/* Panel - Modal en móvil, dropdown en desktop */}
          <div className="fixed sm:absolute inset-x-3 sm:inset-x-auto top-20 sm:top-full sm:right-0 sm:mt-2 sm:w-[340px] bg-white rounded-2xl border border-gray-200 shadow-2xl z-50 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-amber-500 via-amber-400 to-amber-500 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">📊</span>
                <h3 className="text-white font-bold text-sm uppercase tracking-wide">
                  Historial de Cambios
                </h3>
              </div>
              <p className="text-amber-100 text-xs mt-1">
                Cambios en departamentos y extranjero (1 semana)
              </p>
            </div>

            {/* Notifications List */}
            <div className="max-h-[60vh] sm:max-h-[400px] overflow-y-auto">
              {isLoading && notifications.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : isError ? (
                <div className="text-center py-8 px-4">
                  <div className="text-4xl mb-2">⚠️</div>
                  <p className="text-red-500 text-sm">Error al cargar notificaciones</p>
                  <button onClick={() => refresh()} className="mt-2 text-amber-600 text-xs underline">
                    Reintentar
                  </button>
                </div>
              ) : notifications.length === 0 ? (
                <div className="text-center py-8 px-4">
                  <div className="text-4xl mb-2">🔕</div>
                  <p className="text-gray-500 text-sm">
                    No hay cambios registrados en la última semana
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {paginatedNotifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      timeAgo={timeAgo(notification.timestamp)}
                      emoji={getRegionEmoji(notification.region_code)}
                      onClick={() => handleNotificationClick(notification)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Footer with Pagination */}
            {notifications.length > 0 && (
              <div className="bg-gray-50 px-4 py-2 border-t border-gray-200">
                {totalPages > 1 ? (
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                      disabled={currentPage === 0}
                      className="px-2 py-1 text-xs bg-white border border-gray-300 rounded disabled:opacity-50"
                    >
                      ← Ant
                    </button>
                    <span className="text-xs text-gray-500">
                      {currentPage + 1}/{totalPages} • {count} cambios
                    </span>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                      disabled={currentPage >= totalPages - 1}
                      className="px-2 py-1 text-xs bg-white border border-gray-300 rounded disabled:opacity-50"
                    >
                      Sig →
                    </button>
                  </div>
                ) : (
                  <p className="text-center text-xs text-gray-500">
                    Última semana • {count} cambios
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

interface NotificationItemProps {
  notification: Notification;
  timeAgo: string;
  emoji: string;
  onClick: () => void;
}

function NotificationItem({ notification, timeAgo, emoji, onClick }: NotificationItemProps) {
  const { region_name, juntos_change, renovacion_change, gap, leader, actas_percentage } = notification;
  
  // Determine who made progress
  const juntosGained = juntos_change > renovacion_change;
  const renovacionGained = renovacion_change > juntos_change;
  const leaderEmoji = leader === 'POS2' ? '🔴' : leader === 'POS3' ? '🔵' : '⚖️';

  return (
    <button
      onClick={onClick}
      className="w-full px-4 py-3 text-left hover:bg-amber-50 transition-colors"
    >
      {/* Region + Time */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span>{emoji}</span>
          <span className="font-semibold text-gray-900 text-sm">{region_name}</span>
        </div>
        <span className="text-xs text-gray-400">{timeAgo}</span>
      </div>

      {/* Changes */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
        {/* Juntos change */}
        <div className={`flex items-center gap-1 ${juntosGained ? 'font-bold' : ''}`}>
          <span>🔴</span>
          <span className={juntos_change > 0 ? 'text-green-600' : juntos_change < 0 ? 'text-red-600' : 'text-gray-500'}>
            {juntos_change > 0 ? '+' : ''}{juntos_change.toLocaleString('es-PE')}
          </span>
        </div>

        {/* Renovacion change */}
        <div className={`flex items-center gap-1 ${renovacionGained ? 'font-bold' : ''}`}>
          <span>🔵</span>
          <span className={renovacion_change > 0 ? 'text-green-600' : renovacion_change < 0 ? 'text-red-600' : 'text-gray-500'}>
            {renovacion_change > 0 ? '+' : ''}{renovacion_change.toLocaleString('es-PE')}
          </span>
        </div>

        {/* Gap info */}
        <div className="flex items-center gap-1 sm:ml-auto">
          <span className="text-gray-400">Brecha:</span>
          <span className="font-medium text-gray-700">
            {gap.toLocaleString('es-PE')}
          </span>
          <span>{leaderEmoji}</span>
        </div>
      </div>

      {/* Actas progress if available */}
      {actas_percentage !== null && actas_percentage > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-xs text-gray-500">
          <span>📋</span>
          <span>{formatActas(actas_percentage)}% actas</span>
        </div>
      )}
    </button>
  );
}
