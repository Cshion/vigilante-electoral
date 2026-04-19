'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useLiveResults, useRegions, useActasProgress } from '@/hooks/useResults';
import { getProjection, ProjectionData } from '@/lib/api';
import { RivalryDisplay } from '@/components/RivalryDisplay';
import { VoteEvolution } from '@/components/VoteEvolution';
import { LiveIndicator } from '@/components/LiveIndicator';
import { RegionSelector } from '@/components/RegionSelector';
import { NotificationPanel } from '@/components/NotificationPanel';

export default function HomePage() {
  const [selectedRegion, setSelectedRegion] = useState('TOTAL');
  const [projection, setProjection] = useState<ProjectionData | null>(null);
  const { regions, isLoading: regionsLoading } = useRegions();
  // Only need 2 candidates now: Juntos and Renovación
  const { results, isLoading, isError, refresh } = useLiveResults(2, selectedRegion);
  // Fetch actas progress for selected region
  const { actas } = useActasProgress(selectedRegion);

  // Fetch projection data when region changes
  useEffect(() => {
    getProjection(selectedRegion).then(setProjection);
  }, [selectedRegion]);

  const selectedRegionName = results?.region_name || regions?.find((r) => r.code === selectedRegion)?.name || 'Total';

  // Loading state - light theme with fluid animation
  if (isLoading && !results) {
    return (
      <div className="min-h-screen bg-[#fafafa] flex items-center justify-center">
        <div className="text-center px-4">
          {/* Fluid pulsing loader */}
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping" style={{ animationDuration: '1.5s' }}></div>
            <div className="absolute inset-2 rounded-full bg-blue-500/30 animate-pulse" style={{ animationDuration: '1s' }}></div>
            <div className="absolute inset-4 rounded-full bg-blue-600 animate-pulse" style={{ animationDuration: '0.8s' }}></div>
            <span className="absolute inset-0 flex items-center justify-center text-xl">🗳️</span>
          </div>
          <p className="text-gray-600 text-sm animate-pulse">Cargando resultados de ONPE...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="min-h-screen bg-[#fafafa] flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h1 className="text-lg font-bold text-gray-900 mb-2">Error de conexión</h1>
          <p className="text-gray-600 text-sm mb-4">
            No se pudieron cargar los resultados.
          </p>
          <button
            onClick={() => refresh()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium active:bg-blue-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const candidates = results?.candidates || [];
  const totals = results?.totals;
  const rivalry = results?.rivalry;

  // API returns exactly 2 candidates: Juntos Por el Perú (index 0) and Renovación Popular (index 1)
  const juntos = candidates[0];
  const renovacion = candidates[1];

  // Calculate blank and null percentages
  const blankPercent = totals ? (totals.blank_votes / totals.emitted_votes) * 100 : 0;
  const nullPercent = totals ? (totals.null_votes / totals.emitted_votes) * 100 : 0;

  return (
    <div className="min-h-screen bg-[#fafafa]">
      {/* Responsive Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-3 max-w-4xl mx-auto">
          <div className="flex items-center justify-between gap-2">
            <div className="flex-shrink-0">
              <Link href="/" onClick={() => setSelectedRegion('TOTAL')}>
                <h1 className="text-base sm:text-lg md:text-xl font-bold text-gray-900 flex items-center gap-1.5 hover:text-blue-600 transition-colors cursor-pointer">
                  🗳️ Vigilante Electoral
                </h1>
              </Link>
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              <NotificationPanel onRegionSelect={setSelectedRegion} />
              <LiveIndicator timestamp={results?.timestamp} refreshInterval={900} />
            </div>
          </div>
        </div>
        
        {/* Region Filters - Below header */}
        {regions && regions.length > 0 && (
          <div className="bg-gray-50 border-t border-gray-100 px-3 sm:px-4 py-2">
            <div className="max-w-4xl mx-auto">
              <RegionSelector
                regions={regions}
                selectedRegion={selectedRegion}
                onRegionChange={setSelectedRegion}
                isLoading={isLoading || regionsLoading}
              />
            </div>
          </div>
        )}
      </header>

      {/* Main Content - Responsive */}
      <main className="px-4 py-4 md:py-6 max-w-4xl mx-auto">
        {/* The Rivalry - Main Focus */}
        {juntos && renovacion && rivalry && (
          <RivalryDisplay 
            juntos={juntos}
            renovacion={renovacion}
            rivalry={rivalry}
            regionName={selectedRegionName}
            blankPercent={blankPercent}
            nullPercent={nullPercent}
            actasPercentage={actas?.actas_percentage}
            actasCounted={actas?.actas_counted}
            actasTotal={actas?.actas_total}
            projection={projection}
          />
        )}

        {/* Vote Evolution Chart */}
        <VoteEvolution regionCode={selectedRegion} />

        {/* Info Footer */}
        <div className="mt-6 text-center">
          <div className="pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              📋 Los datos mostrados provienen de la web oficial de la ONPE:{' '}
              <a
                href="https://resultadoelectoral.onpe.gob.pe"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline font-medium"
              >
                resultadoelectoral.onpe.gob.pe
              </a>
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Powered by{' '}
              <a
                href="https://www.linkedin.com/company/godatify/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-600 font-medium"
              >
                Datify
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
