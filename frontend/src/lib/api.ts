// API client for electoral data
// STATIC MODE: Data is served from /data/*.json (no backend required)

const IS_STATIC = true; // Set to true for static deployment

// SWR fetcher function - routes to static JSON files
export const fetcher = async <T>(url: string): Promise<T> => {
  if (IS_STATIC) {
    // Map API endpoints to static JSON files
    const staticUrl = mapToStaticUrl(url);
    const response = await fetch(staticUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch static data: ${staticUrl}`);
    }
    return response.json();
  }
  
  // Dynamic mode (legacy)
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const response = await fetch(`${API_URL}${url}`);
  if (!response.ok) {
    throw new Error('Failed to fetch');
  }
  return response.json();
};

// Map API endpoints to static JSON file paths
function mapToStaticUrl(url: string): string {
  // /results/live/regions -> /data/regions.json (must check BEFORE generic /results/live/)
  if (url === '/results/live/regions') {
    return '/data/regions.json';
  }
  
  // /results/live/actas/TOTAL -> /data/actas/TOTAL.json
  if (url.includes('/results/live/actas/')) {
    const match = url.match(/\/results\/live\/actas\/([^?]+)/);
    if (match) {
      return `/data/actas/${match[1]}.json`;
    }
  }
  
  // /results/live/TOTAL?top_n=2 -> /data/results/TOTAL.json
  if (url.startsWith('/results/live/')) {
    const match = url.match(/\/results\/live\/([^?]+)/);
    if (match) {
      return `/data/results/${match[1]}.json`;
    }
  }
  
  // /api/notifications -> /data/notifications.json
  if (url.startsWith('/api/notifications')) {
    return '/data/notifications.json';
  }
  
  // /positions/history -> /data/history/{region}.json
  if (url.startsWith('/positions/history')) {
    const match = url.match(/region_code=([^&]+)/);
    const region = match ? match[1] : 'TOTAL';
    return `/data/history/${region}.json`;
  }
  
  // /positions/projection -> /data/projection/{region}.json
  if (url.startsWith('/positions/projection')) {
    const match = url.match(/region_code=([^&]+)/);
    const region = match ? match[1] : 'TOTAL';
    return `/data/projection/${region}.json`;
  }
  
  // Fallback
  console.warn(`Unknown API route for static mapping: ${url}`);
  return url;
}

// Projection data from TBP algorithm
export interface ProjectionData {
  actas_percentage: number;
  confidence: 'high' | 'medium' | 'low' | 'insufficient';
  snapshots_used: number;
  juntos: {
    current_votes: number;
    projected_votes: number;
    projected_votes_low: number;
    projected_votes_high: number;
    growth_rate_per_pct: number;
    trend_direction: 'increasing' | 'decreasing' | 'stable';
  };
  renovacion: {
    current_votes: number;
    projected_votes: number;
    projected_votes_low: number;
    projected_votes_high: number;
    growth_rate_per_pct: number;
    trend_direction: 'increasing' | 'decreasing' | 'stable';
  };
  projected_leader: string;
  current_leader: string;
  has_contradiction: boolean;
  swap_probability: 'unlikely' | 'possible' | 'likely';
  methodology_text: string;
}

export async function getProjection(regionCode: string = 'TOTAL'): Promise<ProjectionData | null> {
  try {
    return await fetcher<ProjectionData>(`/positions/projection?region_code=${regionCode}`);
  } catch {
    return null;
  }
}
