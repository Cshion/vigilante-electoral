'use client';

import { useState } from 'react';
import { Candidate, Rivalry } from '@/lib/types';
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
}: RivalryDisplayProps) {
  // POS2 = JUNTOS POR EL PERÚ (party_id=10), POS3 = RENOVACIÓN POPULAR (party_id=35)
  // The rivalry.leader field returns "POS2", "POS3", or "TIE"
  const juntosWinning = rivalry.leader === 'POS2';
  const renovacionWinning = rivalry.leader === 'POS3';
  
  // Check if we're viewing TOTAL (national results) or a filtered region
  const isNationalTotal = regionName.toLowerCase().includes('total');
  
  const winnerName = juntosWinning ? 'JUNTOS POR EL PERÚ' : 'RENOVACIÓN POPULAR';

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
          <div className="bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 px-4 py-2 border-b-2 border-blue-700">
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

        {/* Candidates Face-Off */}
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
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none" style={{ marginTop: '20px' }}>
          <div className="bg-gray-900 text-white font-black text-base sm:text-lg px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border-3 sm:border-4 border-white shadow-xl">
            VS
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
        <div className={`px-4 py-3 text-center ${
          juntosWinning 
            ? 'bg-red-600 text-white' 
            : 'bg-sky-600 text-white'
        }`}>
          {isNationalTotal ? (
            // National total - this is who would pass to 2nd round
            <span className="text-sm font-bold uppercase tracking-wider">
              🎯 PASARÍA A 2DA VUELTA: {winnerName}
            </span>
          ) : (
            // Regional filter - just show who's winning in that region
            <span className="text-sm font-bold uppercase tracking-wider">
              📍 LIDERA EN {regionName.toUpperCase()}: {winnerName}
            </span>
          )}
        </div>

        {/* Proyección de Votos Finales - Debajo del resultado */}
        {actasPercentage !== undefined && actasPercentage > 0 && actasPercentage < 100 && (
          <div className="bg-gradient-to-r from-purple-50 via-indigo-50 to-purple-50 px-4 py-3 border-t border-purple-200">
            <div className="text-center mb-2">
              <span className="text-purple-700 font-semibold text-xs uppercase tracking-wide">
                🔮 Proyección al 100% de actas
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="bg-red-100 rounded-lg px-3 py-2">
                <span className="text-red-600 text-xs font-medium block">JUNTOS</span>
                <span className="text-red-700 font-bold text-sm font-mono">
                  {Math.round(juntos.votes * (100 / actasPercentage)).toLocaleString('es-PE')}
                </span>
              </div>
              <div className="bg-sky-100 rounded-lg px-3 py-2">
                <span className="text-sky-600 text-xs font-medium block">RENOVACIÓN</span>
                <span className="text-sky-700 font-bold text-sm font-mono">
                  {Math.round(renovacion.votes * (100 / actasPercentage)).toLocaleString('es-PE')}
                </span>
              </div>
            </div>
            <p className="text-center text-purple-400 text-[10px] mt-2 italic">
              Extrapolación lineal (votos × 100/actas%)
            </p>
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
