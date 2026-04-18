// TypeScript types for electoral data

export interface Region {
  code: string;
  name: string;
  category: 'total' | 'peru' | 'extranjero' | 'departamento';
  ubigeo?: string | null;
}

export interface RegionsResponse {
  regions: Region[];
  total_count: number;
}

export interface ActasProgress {
  region_code: string;
  region_name: string;
  actas_percentage: number;
  actas_counted: number;
  actas_total: number;
  participation: number;
  total_emitted_votes: number;
  total_valid_votes: number;
  timestamp: string;
}

export interface Candidate {
  id: string;
  name: string;
  party_name: string;
  party_id: string;
  votes: number;
  percentage: number;
  party_image_url?: string;
  candidate_image_url?: string;
  vote_change?: number;
  percentage_change?: number;
}

export interface ElectionTotals {
  valid_votes: number;
  blank_votes: number;
  null_votes: number;
  emitted_votes: number;
}

export interface Rivalry {
  leader: string;
  gap: number;
  gap_percent: number;
}

export interface LiveResults {
  election_type: string;
  timestamp: string;
  region_code: string;
  region_name: string;
  candidates: Candidate[];
  rivalry: Rivalry;
  totals: ElectionTotals;
  all_candidates_count: number;
  source: string;
}

// =============================================================================
// Notification types for change tracking
// =============================================================================

export interface Notification {
  id: number;
  region_code: string;
  region_name: string;
  timestamp: string;
  notification_type: string;
  leader: string;
  juntos_votes: number;
  juntos_change: number;
  renovacion_votes: number;
  renovacion_change: number;
  gap: number;
  gap_change: number;
  actas_percentage: number | null;
  message: string;
}

export interface NotificationsResponse {
  notifications: Notification[];
  count: number;
}
