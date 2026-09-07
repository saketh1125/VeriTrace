import type { PipelineStep, RunDetail, SseEnvelope } from '../../lib/types';

export type ConnectionState = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'closed' | 'error';

export interface VerificationState {
  run: RunDetail | null;
  logs: SseEnvelope[];
  connection: ConnectionState;
  starting: boolean;
  startError: string | null;
}

export const initialVerificationState: VerificationState = {
  run: null,
  logs: [],
  connection: 'idle',
  starting: false,
  startError: null,
};

export type VerificationAction =
  | { type: 'START_BEGIN' }
  | { type: 'START_OK'; run: RunDetail }
  | { type: 'START_FAIL'; message: string }
  | { type: 'STATUS'; run: RunDetail }
  | { type: 'EVENT'; envelope: SseEnvelope }
  | { type: 'CONNECTION'; connection: ConnectionState }
  | { type: 'CLEAR_LOGS' };

export const MAX_LOGS = 500;

export function stepForEvent(event: string): PipelineStep | null {
  if (event === 'RUN_STARTED' || event === 'CONSENT_ACCEPTED') return 'VALIDATING_INPUT';
  if (
    event === 'FACE_DETECTION_STARTED' ||
    event === 'FACE_DETECTED' ||
    event === 'EMBEDDING_CREATED'
  )
    return 'PROCESSING_FACE';
  if (event.startsWith('DISCOVERY_')) return 'DISCOVERING';
  if (event.startsWith('MEDIA_FETCH_')) return 'FETCHING_MEDIA';
  if (event === 'CANDIDATE_MATCH_STARTED' || event === 'CANDIDATE_MATCH_RESULT' || event === 'FACE_MATCH')
    return 'MATCHING';
  if (event === 'EVIDENCE_CREATED' || event === 'HASH_COMPUTED') return 'BUILDING_EVIDENCE';
  if (event === 'BLOCKCHAIN_SUBMISSION_STARTED' || event === 'BLOCKCHAIN_SUBMITTED')
    return 'ATTESTING';
  if (event === 'BLOCKCHAIN_VERIFIED' || event === 'BLOCKCHAIN_SUBMISSION_FAILED')
    return 'VERIFYING';
  if (event === 'RUN_COMPLETED') return 'COMPLETED';
  if (event === 'RUN_FAILED') return 'FAILED';
  return null;
}

export function verificationReducer(
  state: VerificationState,
  action: VerificationAction,
): VerificationState {
  switch (action.type) {
    case 'START_BEGIN':
      return { ...initialVerificationState, starting: true };
    case 'START_OK':
      return { ...state, starting: false, startError: null, run: action.run, logs: action.run.events };
    case 'START_FAIL':
      return { ...state, starting: false, startError: action.message };
    case 'STATUS':
      return { ...state, run: action.run };
    case 'EVENT': {
      const logs = [...state.logs, action.envelope].slice(-MAX_LOGS);
      const step = stepForEvent(action.envelope.event);
      const processed =
        action.envelope.event === 'CANDIDATE_MATCH_RESULT'
          ? (state.run?.processed_count ?? 0) + 1
          : state.run?.processed_count;
      return {
        ...state,
        logs,
        run: state.run
          ? {
              ...state.run,
              pipeline_step: step ?? state.run.pipeline_step,
              processed_count: processed ?? state.run.processed_count,
            }
          : state.run,
      };
    }
    case 'CONNECTION':
      return { ...state, connection: action.connection };
    case 'CLEAR_LOGS':
      return { ...state, logs: [] };
  }
}
