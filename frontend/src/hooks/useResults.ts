'use client';

import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { LiveResults, RegionsResponse, ActasProgress } from '@/lib/types';

// Global SWR config for caching - respects server cache-control headers
const defaultSwrConfig = {
  refreshInterval: 300000,   // Poll every 5 minutes (matches server cache TTL)
  revalidateOnFocus: false,  // Don't refetch when tab regains focus
  revalidateOnReconnect: false, // Don't refetch on reconnect
  dedupingInterval: 300000,  // Dedupe requests for 5 minutes (matches cache TTL)
  revalidateIfStale: false,  // Don't revalidate if data is stale (trust server cache)
};

/**
 * Hook for fetching LIVE election results directly from ONPE
 * Polls every 5 minutes for updates
 * @param topN - Number of top candidates to return
 * @param regionCode - Optional region code (defaults to 'NACIONAL' if not provided)
 */
export function useLiveResults(topN = 3, regionCode?: string) {
  // Use regional endpoint if region specified, otherwise use default
  const endpoint = regionCode 
    ? `/results/live/${regionCode}?top_n=${topN}`
    : `/results/live?top_n=${topN}`;

  const { data, error, isLoading, mutate } = useSWR<LiveResults>(
    endpoint,
    fetcher,
    defaultSwrConfig
  );

  return {
    results: data,
    isLoading,
    isError: error,
    refresh: mutate,
  };
}

/**
 * Hook for fetching actas (ballot) counting progress
 * @param regionCode - Region code to fetch actas for
 */
export function useActasProgress(regionCode: string) {
  const { data, error, isLoading, mutate } = useSWR<ActasProgress>(
    regionCode ? `/results/live/actas/${regionCode}` : null,
    fetcher,
    defaultSwrConfig
  );

  return {
    actas: data,
    isLoading,
    isError: error,
    refresh: mutate,
  };
}

/**
 * Hook for fetching available regions
 */
export function useRegions() {
  const { data, error, isLoading } = useSWR<RegionsResponse>(
    '/results/live/regions',
    fetcher,
    {
      ...defaultSwrConfig,
      refreshInterval: 0, // Regions don't change - no polling needed
    }
  );

  return {
    regions: data?.regions, // Extract regions array from response object
    isLoading,
    isError: error,
  };
}

/**
 * Hook for fetching change notifications (historial de cambios)
 * 
 * ⚡ SIMPLIFIED: Sin tracking de "leído" porque las notificaciones son
 * compartidas entre todos los usuarios. Solo muestra cambios recientes.
 * 
 * ⚡ OPTIMIZED: Backend cachea 5 min. Frontend poll cada 5 minutos.
 * SWR deduplica automáticamente.
 */
export function useNotifications(limit = 50, hours = 12) {
  const { data, error, isLoading, mutate } = useSWR<import('@/lib/types').NotificationsResponse>(
    `/api/notifications?limit=${limit}&hours=${hours}`,
    fetcher,
    defaultSwrConfig
  );

  return {
    notifications: data?.notifications || [],
    count: data?.count || 0,
    isLoading,
    isError: error,
    refresh: mutate,
  };
}
