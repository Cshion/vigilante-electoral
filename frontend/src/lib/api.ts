// API client for electoral backend

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// SWR fetcher function
export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await fetch(`${API_URL}${url}`);
  if (!response.ok) {
    throw new Error('Failed to fetch');
  }
  return response.json();
};

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
    const res = await fetch(`${API_URL}/positions/projection?region_code=${regionCode}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
