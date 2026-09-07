// Backend run contract shapes. Rendered only; never re-derived here.

export type PipelineStep =
  | 'IDLE'
  | 'VALIDATING_INPUT'
  | 'PROCESSING_FACE'
  | 'DISCOVERING'
  | 'FETCHING_MEDIA'
  | 'MATCHING'
  | 'BUILDING_EVIDENCE'
  | 'ATTESTING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'FAILED';

export type RunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface SseEnvelope {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  event: string;
  run_id: string;
  candidate_id?: string | null;
  data: Record<string, unknown>;
}

export interface Candidate {
  candidate_id: string;
  post_url: string;
  platform: string;
  author?: string | null;
  published_at?: string | null;
  media_url: string;
  media_type: string;
  status: string;
  face_similarity?: number | null;
  image_similarity?: number | null;
  reason?: string | null;
}

export interface BlockchainState {
  network: string;
  chain_id: number;
  registry?: string | null;
  evidence_hash?: string | null;
  status: string;
  tx_hash?: string | null;
  integrity: string;
}

export interface EvidenceState {
  post_url: string;
  platform: string;
  media_url: string;
  media_sha256?: string | null;
  evidence_sha256?: string | null;
  face_similarity?: number | null;
  image_similarity?: number | null;
  face_threshold?: number | null;
}

export interface RunResult {
  outcome: string;
  evidence?: EvidenceState | null;
  blockchain: BlockchainState;
}

export interface RunDetail {
  run_id: string;
  status: RunStatus;
  pipeline_step: PipelineStep;
  platform: string;
  method: string;
  target: string;
  max_posts: number;
  attest: boolean;
  created_at: string;
  updated_at: string;
  duration_ms?: number | null;
  candidate_count: number;
  processed_count: number;
  error_code?: string | null;
  error_message?: string | null;
  candidates: Candidate[];
  result?: RunResult | null;
  events: SseEnvelope[];
}

export interface RunSummary {
  run_id: string;
  status: string;
  pipeline_step: string;
  platform: string;
  method: string;
  target: string;
  created_at: string;
  updated_at: string;
  duration_ms?: number | null;
  candidate_count: number;
  processed_count: number;
  error_code?: string | null;
  error_message?: string | null;
  outcome?: string | null;
  event_count: number;
}

export interface PreflightResult {
  ok: boolean;
  faces_detected?: number;
  det_score?: number;
  error_code?: string;
  message?: string;
}

export interface Diagnostics {
  api: { status: string };
  apify: { configured: boolean };
  face: {
    model: string;
    detection_size: [number, number];
    min_detection_score: number;
    min_face_size: number;
    match_threshold: number;
    matching_policy: string;
    loaded: boolean;
  };
  discovery: { default_limit: number; max_candidates: number };
  blockchain: {
    network: string;
    chain_id: number;
    registry_configured: boolean;
    rpc_configured: boolean;
  };
}
