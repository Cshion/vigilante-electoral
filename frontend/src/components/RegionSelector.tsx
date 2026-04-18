'use client';

import { useState, useRef, useEffect } from 'react';
import { Region } from '@/lib/types';

interface RegionSelectorProps {
  regions: Region[];
  selectedRegion: string;
  onRegionChange: (regionCode: string) => void;
  isLoading?: boolean;
}

/**
 * Region selector with separated pill buttons centered:
 * [ Total ]  [ Perú ]  [ Exterior ]  [ Departamento ▼ ]
 */
export function RegionSelector({
  regions,
  selectedRegion,
  onRegionChange,
  isLoading,
}: RegionSelectorProps) {
  const [showDepartments, setShowDepartments] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Group regions by category
  const grouped = {
    total: regions.find((r) => r.category === 'total'),
    peru: regions.find((r) => r.category === 'peru'),
    extranjero: regions.find((r) => r.category === 'extranjero'),
    departamentos: regions
      .filter((r) => r.category === 'departamento')
      .sort((a, b) => a.name.localeCompare(b.name, 'es')),
  };

  // Check if current selection is a department
  const isDepartmentSelected = grouped.departamentos.some(d => d.code === selectedRegion);
  const selectedDepartment = grouped.departamentos.find(d => d.code === selectedRegion);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDepartments(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowDepartments(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const handleQuickSelect = (code: string) => {
    onRegionChange(code);
    setShowDepartments(false);
  };

  const handleDepartmentSelect = (code: string) => {
    onRegionChange(code);
    setShowDepartments(false);
  };

  // Button styles - separated pills
  const pillBase = "px-4 py-2 text-sm font-medium rounded-full transition-all duration-150";
  const pillActive = "bg-gray-900 text-white shadow-md";
  const pillInactive = "bg-white text-gray-600 hover:bg-gray-100 hover:text-gray-900 border border-gray-200";

  return (
    <div className="flex items-center justify-center w-full" ref={dropdownRef}>
      {/* Centered pill buttons */}
      <div className="flex items-center gap-2">
        {/* TOTAL */}
        {grouped.total && (
          <button
            onClick={() => handleQuickSelect(grouped.total!.code)}
            disabled={isLoading}
            className={`${pillBase} ${selectedRegion === grouped.total.code ? pillActive : pillInactive}`}
          >
            Total
          </button>
        )}

        {/* PERÚ */}
        {grouped.peru && (
          <button
            onClick={() => handleQuickSelect(grouped.peru!.code)}
            disabled={isLoading}
            className={`${pillBase} ${selectedRegion === grouped.peru.code ? pillActive : pillInactive}`}
          >
            Perú
          </button>
        )}

        {/* EXTRANJERO */}
        {grouped.extranjero && (
          <button
            onClick={() => handleQuickSelect(grouped.extranjero!.code)}
            disabled={isLoading}
            className={`${pillBase} ${selectedRegion === grouped.extranjero.code ? pillActive : pillInactive}`}
          >
            Exterior
          </button>
        )}

        {/* POR DEPARTAMENTO - Dropdown */}
        {grouped.departamentos.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowDepartments(!showDepartments)}
              disabled={isLoading}
              className={`${pillBase} ${isDepartmentSelected ? pillActive : pillInactive} flex items-center gap-1.5`}
            >
              {isDepartmentSelected && selectedDepartment ? (
                <span className="truncate max-w-[100px]">{selectedDepartment.name}</span>
              ) : (
                <span>Departamento</span>
              )}
              <svg 
                className={`w-3.5 h-3.5 flex-shrink-0 transition-transform duration-200 ${showDepartments ? 'rotate-180' : ''}`} 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown Panel */}
            {showDepartments && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-52 max-h-[50vh] overflow-y-auto bg-white rounded-xl border border-gray-200 shadow-xl z-50">
                {/* Header */}
                <div className="sticky top-0 px-3 py-2 bg-gray-50 border-b border-gray-100 rounded-t-xl">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Departamentos
                  </span>
                </div>
                
                {/* List */}
                <div className="p-1.5">
                  {grouped.departamentos.map((dept) => (
                    <button
                      key={dept.code}
                      onClick={() => handleDepartmentSelect(dept.code)}
                      className={`
                        w-full text-left px-3 py-2 text-sm rounded-lg transition-colors
                        ${selectedRegion === dept.code
                          ? 'bg-gray-900 text-white font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                        }
                      `}
                    >
                      {dept.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact region badge showing current selection
 */
export function RegionBadge({ regionName }: { regionName: string }) {
  // Don't show badge for Total (it's the default view)
  if (regionName.includes('Total') || regionName === 'Resultados Nacionales') {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      {regionName}
    </span>
  );
}
