'use client';

import { useState } from 'react';
import { Candidate, Rivalry } from '@/lib/types';
import { ProjectionData } from '@/lib/api';
import { formatActas } from '@/lib/utils';
import Image from 'next/image';

interface RivalryDisplayProps {
  juntos: Candidate;
  renovacion: Candidate;
  rivalry: Rivalry;
  regionName: string;
  blankPercent?: number;
  nullPercent?: number;
  actasPercentage?: number;
  actasCounted?: number;
  actasTotal?: number;
  projection?: ProjectionData | null;
}

// Tooltip component for the disclaimer info icon - mobile-friendly with tap
// Uses fixed positioning on mobile to escape overflow:hidden containers
function InfoTooltip({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <>
      {/* Backdrop overlay to close on tap outside (mobile) */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-[9998] sm:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
      
      <div className="relative inline-flex items-center">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          className="cursor-help text-purple-400 hover:text-purple-600 active:text-purple-700 
                     transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center
                     -m-2 p-2 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-300"
          aria-label="Más información"
          aria-expanded={isOpen}
        >
          <span className="text-base">ⓘ</span>
        </button>
        
        {/* Mobile: FIXED positioning centered on screen (escapes overflow:hidden) */}
        {/* Desktop: absolute positioning above the icon */}
        <div 
          className={`transition-all duration-200
                      ${isOpen ? 'visible opacity-100' : 'invisible opacity-0 pointer-events-none'}
                      
                      /* Mobile: fixed, centered on screen */
                      fixed z-[9999] bottom-4 left-4 right-4
                      
                      /* Desktop: absolute, above icon */
                      sm:absolute sm:bottom-full sm:left-1/2 sm:-translate-x-1/2 sm:mb-2
                      sm:right-auto sm:w-72
                      
                      p-4 sm:p-3 bg-gray-900 text-white text-sm sm:text-xs leading-relaxed 
                      rounded-xl sm:rounded-lg shadow-2xl`}
          role="tooltip"
        >
          {/* Close button for mobile */}
          <button 
            onClick={() => setIsOpen(false)}
            className="absolute top-2 right-2 text-gray-400 hover:text-white sm:hidden
                       w-8 h-8 flex items-center justify-center"
            aria-label="Cerrar"
          >
            ✕
          </button>
          
          {/* Arrow - only on desktop */}
          <div className="hidden sm:block absolute left-1/2 -translate-x-1/2
                          -bottom-2 border-8 border-transparent border-t-gray-900" />
          
          <div className="pr-6 sm:pr-0">
            {children}
          </div>
        </div>
      </div>
    </>
  );
}

// Local images for parties (downloaded from ONPE)
// If images don't exist, we use styled placeholders
const LOCAL_IMAGES = {
  JUNTOS: {
    party: '/partidos/00000010.jpg',
    candidate: '/candidatos/16002918.jpg',
    partyName: 'JUNTOS POR EL PERÚ',
    initials: 'JP',
    colors: 'from-red-600 via-red-500 to-green-600',
  },
  RENOVACION: {
    party: '/partidos/00000035.jpg',
    candidate: '/candidatos/07845838.jpg',
    partyName: 'RENOVACIÓN POPULAR',
    initials: 'RP',
    colors: 'from-sky-500 to-sky-700',
  },
};

// Party color schemes
const PARTY_COLORS = {
  JUNTOS: {
    primary: '#dc2626', // red-600
    secondary: '#fef2f2', // red-50
    gradient: 'from-red-500 to-green-500',
  },
  RENOVACION: {
    primary: '#0284c7', // sky-600
    secondary: '#f0f9ff', // sky-50
    gradient: 'from-sky-400 to-sky-600',
  },
};

export function RivalryDisplay({
  juntos,
  renovacion,
  rivalry,
  regionName,
  blankPercent,
  nullPercent,
  actasPercentage,
  actasCounted,
  actasTotal,
  projection,
}: RivalryDisplayProps) {
  // POS2 = JUNTOS POR EL PERÚ (party_id=10), POS3 = RENOVACIÓN POPULAR (party_id=35)
  // The rivalry.leader field returns "POS2", "POS3", or "TIE"
  const juntosWinning = rivalry.leader === 'POS2';
  const renovacionWinning = rivalry.leader === 'POS3';
  
  // Check if we're viewing TOTAL (national results) or a filtered region
  const isNationalTotal = regionName.toLowerCase().includes('total');
  
  const winnerName = juntosWinning ? 'JUNTOS POR EL PERÚ' : 'RENOVACIÓN POPULAR';
  const winnerShortName = juntosWinning ? 'JUNTOS' : 'RENOVACIÓN';
  
  // Use projection data from backend if available, otherwise fallback to simple calculation
  const juntosProjected = projection?.juntos.projected_votes ?? 
    (actasPercentage && actasPercentage > 0 
      ? Math.round(juntos.votes * (100 / actasPercentage)) 
      : juntos.votes);
  const renovacionProjected = projection?.renovacion.projected_votes ?? 
    (actasPercentage && actasPercentage > 0 
      ? Math.round(renovacion.votes * (100 / actasPercentage)) 
      : renovacion.votes);
  
  // Determine leaders for display
  const projectedLeader = juntosProjected > renovacionProjected ? 'POS2' : 'POS3';
  const currentLeader = rivalry.leader;
  
  // Use backend contradiction detection if available
  const hasContradiction = projection?.has_contradiction ?? (
    actasPercentage !== undefined && 
    actasPercentage > 0 && 
    actasPercentage < 100 && 
    projectedLeader !== currentLeader &&
    currentLeader !== 'TIE'
  );
  
  const projectedWinnerName = projectedLeader === 'POS2' ? 'JUNTOS' : 'RENOVACIÓN';
  const currentWinnerName = currentLeader === 'POS2' ? 'JUNTOS' : 'RENOVACIÓN';

  return (
    <div className="space-y-4">
      {/* THE SHOWDOWN */}
      <div className="relative bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-lg">
        {/* Header - BATALLA POR LA 2da VUELTA */}
        <div className="relative bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 px-4 py-4">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxjaXJjbGUgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMSkiIGN4PSIyMCIgY3k9IjIwIiByPSIxIi8+PC9nPjwvc3ZnPg==')] opacity-30"></div>
          <h2 className="text-center text-white font-black text-lg md:text-xl uppercase tracking-widest relative">
            ⚔️ BATALLA POR LA 2da VUELTA
          </h2>
        </div>

        {/* Actas Progress Banner */}
        {actasPercentage !== undefined && (
          <div className="bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 px-4 py-2">
            <div className="flex items-center justify-center gap-2">
              <span className="text-white font-black text-sm uppercase tracking-wide">
                📊 Actas: {formatActas(actasPercentage)}%
              </span>
              {actasCounted !== undefined && actasTotal !== undefined && (
                <span className="text-blue-100 text-xs font-medium">
                  ({actasCounted.toLocaleString('es-PE')} / {actasTotal.toLocaleString('es-PE')})
                </span>
              )}
            </div>
          </div>
        )}

        {/* Candidates Face-Off with VS Badge */}
        <div className="relative">
          <div className="grid grid-cols-2 divide-x-2 divide-gray-200">
            {/* JUNTOS POR EL PERÚ */}
            <PartyColumn
              candidate={juntos}
              isWinning={juntosWinning}
              isJuntos={true}
            />

            {/* RENOVACIÓN POPULAR */}
            <PartyColumn
              candidate={renovacion}
              isWinning={renovacionWinning}
              isJuntos={false}
            />
          </div>

          {/* VS Badge - Centered between columns */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            <div className="bg-gray-900 text-white font-black text-base sm:text-lg px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border-3 sm:border-4 border-white shadow-xl">
              VS
            </div>
          </div>
        </div>

        {/* Vote Difference - Simple and clear */}
        <div className={`px-4 py-4 border-t-2 ${
          juntosWinning 
            ? 'bg-gradient-to-r from-red-100 via-red-50 to-white border-red-300' 
            : 'bg-gradient-to-l from-sky-100 via-sky-50 to-white border-sky-300'
        }`}>
          {/* Vote Difference - Big and clear */}
          <div className="text-center">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl ${
              juntosWinning 
                ? 'bg-red-500 text-white' 
                : 'bg-sky-500 text-white'
            } shadow-lg`}>
              <span className="text-2xl">{juntosWinning ? '🔴' : '🔵'}</span>
              <div>
                <span className="font-black text-xl md:text-2xl font-mono">
                  +{rivalry.gap.toLocaleString('es-PE')}
                </span>
                <span className="text-sm ml-1 opacity-90">votos</span>
              </div>
            </div>
          </div>
        </div>

        {/* Result Banner - Contextual based on region */}
        <div className={`px-3 sm:px-4 py-3 text-center ${
          juntosWinning 
            ? 'bg-red-600 text-white' 
            : 'bg-sky-600 text-white'
        }`}>
          {isNationalTotal ? (
            // National total - show who's leading (full party name, no duplicate ventaja)
            <span className="text-xs sm:text-sm font-bold uppercase tracking-wider flex items-center justify-center gap-2">
              🟢 {winnerName} LIDERA
            </span>
          ) : (
            // Regional filter - show who's winning in that region (full name, no duplicate gap)
            <span className="text-xs sm:text-sm font-bold uppercase tracking-wider flex items-center justify-center gap-2 flex-wrap">
              📍 {winnerName} LIDERA EN {regionName.toUpperCase()}
            </span>
          )}
        </div>


        {/* Proyección de Votos Finales - Debajo del resultado */}
        {actasPercentage !== undefined && actasPercentage > 0 && actasPercentage < 100 && (
          <div className="relative bg-gradient-to-r from-purple-50/70 via-indigo-50/70 to-purple-50/70 
                          px-4 py-3 border-2 border-dashed border-purple-300 rounded-b-lg
                          opacity-90 hover:opacity-100 transition-opacity">
            {/* Projection header with trend icon */}
            <div className="text-center mb-2">
              <span className="text-purple-700 font-semibold text-xs uppercase tracking-wide flex items-center justify-center gap-2">
                <span className="text-base">📈</span>
                Si la tendencia continúa...
              </span>
              <p className="text-purple-500 text-[10px] mt-0.5">
                Proyección al 100% de actas
              </p>
            </div>
            
            {/* Projected votes grid */}
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className={`rounded-lg px-3 py-2 border border-dashed ${
                juntosProjected > renovacionProjected 
                  ? 'bg-red-100/80 border-red-300' 
                  : 'bg-red-50/60 border-red-200'
              }`}>
                <span className="text-red-600 text-[10px] font-medium block leading-tight">
                  {LOCAL_IMAGES.JUNTOS.partyName}
                </span>
                <span className="text-red-700 font-bold text-sm font-mono">
                  {juntosProjected.toLocaleString('es-PE')}
                </span>
                {juntosProjected > renovacionProjected && (
                  <span className="text-green-600 text-[10px] block mt-0.5">▲ Lidera en tendencia</span>
                )}
              </div>
              <div className={`rounded-lg px-3 py-2 border border-dashed ${
                renovacionProjected > juntosProjected 
                  ? 'bg-sky-100/80 border-sky-300' 
                  : 'bg-sky-50/60 border-sky-200'
              }`}>
                <span className="text-sky-600 text-[10px] font-medium block leading-tight">
                  {LOCAL_IMAGES.RENOVACION.partyName}
                </span>
                <span className="text-sky-700 font-bold text-sm font-mono">
                  {renovacionProjected.toLocaleString('es-PE')}
                </span>
                {renovacionProjected > juntosProjected && (
                  <span className="text-green-600 text-[10px] block mt-0.5">▲ Lidera en tendencia</span>
                )}
              </div>
            </div>
            
            {/* Always-visible disclaimer with tooltip */}
            <div className="flex items-center justify-center gap-1 sm:gap-1.5 mt-3 py-2.5 sm:py-2 
                            bg-purple-100/50 rounded border border-purple-200 min-h-[44px]">
              <InfoTooltip>
                {projection ? (
                  <>
                    Analizamos todo el historial del conteo oficial para calcular la velocidad de 
                    crecimiento de cada partido. Usamos suavizado exponencial (EWMA): 
                    los cambios más recientes pesan más que los antiguos.
                  </>
                ) : (
                  'Proyección simple: votos actuales × (100 / % actas contadas).'
                )}
              </InfoTooltip>
              <p className="text-purple-600 text-[10px] sm:text-[11px] font-medium leading-tight">
                Estimación matemática. Puede cambiar.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface PartyColumnProps {
  candidate: Candidate;
  isWinning: boolean;
  isJuntos: boolean;
}

function PartyColumn({ candidate, isWinning, isJuntos }: PartyColumnProps) {
  const [partyImgError, setPartyImgError] = useState(false);
  const [candidateImgError, setCandidateImgError] = useState(false);
  
  // Party-specific background colors: red for JUNTOS, sky/celeste for RENOVACIÓN
  const partyBgColor = isJuntos ? 'bg-red-50' : 'bg-sky-50';
  const localImages = isJuntos ? LOCAL_IMAGES.JUNTOS : LOCAL_IMAGES.RENOVACION;
  
  return (
    <div
      className={`relative p-4 md:p-6 transition-all duration-300 ${
        isWinning
          ? 'bg-gradient-to-b from-green-50 to-emerald-50 ring-4 ring-inset ring-green-400'
          : partyBgColor
      }`}
    >
      {/* Party Logo or Fallback */}
      <div className="text-center mt-2">
        <div className="flex justify-center mb-2">
          {!partyImgError ? (
            <Image
              src={localImages.party}
              alt={localImages.partyName}
              width={72}
              height={72}
              className={`rounded-xl shadow-md ${
                isWinning ? 'ring-4 ring-green-400' : ''
              }`}
              unoptimized
              onError={() => setPartyImgError(true)}
            />
          ) : (
            <div
              className={`w-[72px] h-[72px] rounded-xl shadow-md flex items-center justify-center text-2xl font-black text-white bg-gradient-to-br ${localImages.colors} ${
                isWinning ? 'ring-4 ring-green-400' : ''
              }`}
            >
              {localImages.initials}
            </div>
          )}
        </div>

        {/* Party Name */}
        <h3
          className={`text-sm md:text-base font-black leading-tight mb-2 ${
            isWinning ? 'text-green-700' : 'text-gray-800'
          }`}
        >
          {localImages.partyName}
        </h3>

        {/* Candidate Photo or Fallback */}
        <div className="flex justify-center mb-2">
          {!candidateImgError ? (
            <Image
              src={localImages.candidate}
              alt="Candidato"
              width={48}
              height={48}
              className={`rounded-full border-2 shadow-md ${
                isWinning ? 'border-green-400' : 'border-white'
              }`}
              unoptimized
              onError={() => setCandidateImgError(true)}
            />
          ) : (
            <div
              className={`w-12 h-12 rounded-full flex items-center justify-center shadow-md ${
                isJuntos ? 'bg-red-200 border-2 border-red-300' : 'bg-sky-200 border-2 border-sky-300'
              } ${isWinning ? 'ring-2 ring-green-400' : ''}`}
            >
              <span className="text-xl">👤</span>
            </div>
          )}
        </div>
      </div>

      {/* Vote Stats */}
      <div className="mt-3 text-center">
        {/* Votes */}
        <p
          className={`text-2xl md:text-3xl font-mono font-black ${
            isWinning ? 'text-green-700' : 'text-gray-900'
          }`}
        >
          {candidate.votes.toLocaleString('es-PE')}
        </p>
        <p className="text-xs text-gray-500 uppercase tracking-wide">votos</p>

        {/* Vote Change */}
        {candidate.vote_change !== undefined && candidate.vote_change !== 0 && (
          <div
            className={`mt-2 py-1 px-2 rounded text-sm font-mono font-bold ${
              candidate.vote_change > 0
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {candidate.vote_change > 0 ? '+' : ''}
            {candidate.vote_change.toLocaleString('es-PE')}
          </div>
        )}
      </div>
    </div>
  );
}
