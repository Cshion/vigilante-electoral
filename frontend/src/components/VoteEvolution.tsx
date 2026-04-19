'use client';

import { useEffect, useState } from 'react';
import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { formatActas } from '@/lib/utils';

// Match the actual API response format
interface PositionHistoryResponse {
  hours: number;
  snapshots: PositionSnapshot[];
  total: number;
}

interface PositionSnapshot {
  id: number;
  timestamp: string;
  segundo: {
    nombre: string;
    votos: number;
    porcentaje: number;
  };
  tercero: {
    nombre: string;
    votos: number;
    porcentaje: number;
  };
  diferencia_votos: number;
  diferencia_porcentaje: number;
  blancos_porcentaje?: number;
  nulos_porcentaje?: number;
  // Actas progress
  actas_porcentaje?: number;
  actas_contabilizadas?: number;
  actas_total?: number;
}

// Party name mapping
const PARTY_NAMES: Record<string, string> = {
  'SANCHEZ': 'JUNTOS POR EL PERÚ',
  'LOPEZ': 'RENOVACIÓN POPULAR',
};

function getPartyName(candidateName: string): string {
  if (candidateName.toUpperCase().includes('SANCHEZ')) {
    return PARTY_NAMES['SANCHEZ'];
  }
  if (candidateName.toUpperCase().includes('LOPEZ') || candidateName.toUpperCase().includes('LÓPEZ')) {
    return PARTY_NAMES['LOPEZ'];
  }
  return candidateName;
}

interface VoteEvolutionProps {
  regionCode?: string;
}

const ITEMS_PER_PAGE = 15;

export function VoteEvolution({ regionCode }: VoteEvolutionProps) {
  const [currentPage, setCurrentPage] = useState(0);
  
  // Build API URL with optional region filter
  // Use 168 hours (1 week) to ensure all historical data is visible
  const apiUrl = regionCode
    ? `/positions/history?hours=168&limit=100&region_code=${regionCode}`
    : '/positions/history?hours=168&limit=100';

  const { data, isLoading } = useSWR<PositionHistoryResponse>(
    apiUrl,
    fetcher,
    { 
      refreshInterval: 300000, // Refresh every 5 minutes (matches server cache)
      revalidateOnFocus: false, // Don't spam on tab switch
      revalidateOnReconnect: false,
      dedupingInterval: 300000, // Dedupe for 5 minutes
    }
  );

  const history = data?.snapshots || [];
  const totalPages = Math.ceil(history.length / ITEMS_PER_PAGE);
  const paginatedHistory = history.slice(
    currentPage * ITEMS_PER_PAGE,
    (currentPage + 1) * ITEMS_PER_PAGE
  );

  // Reset to page 0 when region changes
  useEffect(() => {
    setCurrentPage(0);
  }, [regionCode]);

  if (isLoading) {
    return (
      <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-40 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-2">� Historial de Cambios</h3>
        <p className="text-base text-gray-500 text-center py-10">
          Sin datos históricos aún. Los cambios aparecerán aquí cuando ONPE actualice y los votos cambien.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg md:text-xl font-bold text-gray-800">
          📊 Historial de Cambios
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Solo se registra cuando ONPE actualiza los votos
        </p>
      </div>
      
      {/* Table Header */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100 border-b border-gray-200">
            <tr>
              <th className="px-2 md:px-4 py-2 md:py-3 text-left text-[10px] md:text-xs font-bold text-gray-600 uppercase tracking-wider whitespace-nowrap">
                Hora
              </th>
              <th className="px-2 md:px-4 py-2 md:py-3 text-center text-[10px] md:text-xs font-bold text-blue-600 uppercase tracking-wider bg-blue-50 whitespace-nowrap">
                Actas
              </th>
              <th className="px-2 md:px-4 py-2 md:py-3 text-center text-[10px] md:text-xs font-bold text-red-600 uppercase tracking-wider bg-red-50 whitespace-nowrap">
                <span className="hidden md:inline">🔴 JUNTOS POR EL PERÚ</span>
                <span className="md:hidden">🔴 JP</span>
              </th>
              <th className="px-2 md:px-4 py-2 md:py-3 text-center text-[10px] md:text-xs font-bold text-sky-600 uppercase tracking-wider bg-sky-50 whitespace-nowrap">
                <span className="hidden md:inline">🔵 RENOVACIÓN POPULAR</span>
                <span className="md:hidden">🔵 RP</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {paginatedHistory.map((snapshot, i) => {
              const actualIndex = currentPage * ITEMS_PER_PAGE + i;
              return (
                <ChangeRow 
                  key={snapshot.id} 
                  snapshot={snapshot} 
                  prevSnapshot={history[actualIndex + 1]} 
                  isLatest={actualIndex === 0}
                />
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Página {currentPage + 1} de {totalPages} ({history.length} registros)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="px-3 py-1 text-sm bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              ← Ant
            </button>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className="px-3 py-1 text-sm bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Sig →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ChangeRow({ 
  snapshot, 
  prevSnapshot,
  isLatest 
}: { 
  snapshot: PositionSnapshot; 
  prevSnapshot?: PositionSnapshot;
  isLatest?: boolean;
}) {
  // Calculate vote changes
  const pos2Change = prevSnapshot ? snapshot.segundo.votos - prevSnapshot.segundo.votos : 0;
  const pos3Change = prevSnapshot ? snapshot.tercero.votos - prevSnapshot.tercero.votos : 0;
  // Calculate actas change
  const actasChange = prevSnapshot && snapshot.actas_porcentaje !== undefined && prevSnapshot.actas_porcentaje !== undefined
    ? snapshot.actas_porcentaje - prevSnapshot.actas_porcentaje
    : 0;
  
  return (
    <tr className={`hover:bg-gray-50 ${isLatest ? 'bg-yellow-50' : ''}`}>
      {/* Timestamp */}
      <td className="px-2 md:px-4 py-3 md:py-4">
        <div className="flex flex-col">
          <span className="text-sm md:text-base font-bold text-gray-900 whitespace-nowrap">
            {formatTimeOnly(snapshot.timestamp)}
          </span>
          <span className="text-[10px] md:text-xs text-gray-500">
            {formatDateOnly(snapshot.timestamp)}
          </span>
          {isLatest && (
            <span className="text-[10px] text-yellow-600 font-semibold">
              ⭐ NUEVO
            </span>
          )}
        </div>
      </td>
      
      {/* Actas Progress */}
      <td className="px-2 md:px-4 py-3 md:py-4 bg-blue-50/50">
        <div className="text-center">
          <span className="text-sm md:text-lg font-mono font-bold text-blue-700">
            {formatActas(snapshot.actas_porcentaje)}%
          </span>
        </div>
      </td>
      
      {/* JUNTOS POR EL PERÚ - Votos */}
      <td className="px-2 md:px-4 py-3 md:py-4 bg-red-50/50">
        <div className="text-center">
          <span className="text-xs md:text-base font-mono font-bold text-red-700">
            {snapshot.segundo.votos.toLocaleString('es-PE')}
          </span>
          {pos2Change !== 0 && (
            <div className={`text-[10px] md:text-sm font-mono font-bold ${pos2Change > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {pos2Change > 0 ? '+' : ''}{pos2Change.toLocaleString('es-PE')}
            </div>
          )}
        </div>
      </td>
      
      {/* RENOVACIÓN POPULAR - Votos */}
      <td className="px-2 md:px-4 py-3 md:py-4 bg-sky-50/50">
        <div className="text-center">
          <span className="text-xs md:text-base font-mono font-bold text-sky-700">
            {snapshot.tercero.votos.toLocaleString('es-PE')}
          </span>
          {pos3Change !== 0 && (
            <div className={`text-[10px] md:text-sm font-mono font-bold ${pos3Change > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {pos3Change > 0 ? '+' : ''}{pos3Change.toLocaleString('es-PE')}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

function formatTimeOnly(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleTimeString('es-PE', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch {
    return '';
  }
}

function formatDateOnly(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleDateString('es-PE', {
      weekday: 'short',
      day: 'numeric',
      month: 'short'
    });
  } catch {
    return '';
  }
}
