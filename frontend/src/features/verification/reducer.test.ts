import { describe, expect, it } from 'vitest';
import {
  MAX_LOGS,
  initialVerificationState,
  stepForEvent,
  verificationReducer,
} from './reducer';
import type { SseEnvelope } from '../../lib/types';

function envelope(event: string): SseEnvelope {
  return {
    timestamp: new Date().toISOString(),
    level: 'INFO',
    event,
    run_id: 'vr_test',
    data: {},
  };
}

describe('stepForEvent', () => {
  it('mirrors the backend pipeline without inventing states', () => {
    expect(stepForEvent('CONSENT_ACCEPTED')).toBe('VALIDATING_INPUT');
    expect(stepForEvent('EMBEDDING_CREATED')).toBe('PROCESSING_FACE');
    expect(stepForEvent('DISCOVERY_PROGRESS')).toBe('DISCOVERING');
    expect(stepForEvent('MEDIA_FETCH_STARTED')).toBe('FETCHING_MEDIA');
    expect(stepForEvent('CANDIDATE_MATCH_RESULT')).toBe('MATCHING');
    expect(stepForEvent('FACE_MATCH')).toBe('MATCHING');
    expect(stepForEvent('HASH_COMPUTED')).toBe('BUILDING_EVIDENCE');
    expect(stepForEvent('BLOCKCHAIN_SUBMITTED')).toBe('ATTESTING');
    expect(stepForEvent('BLOCKCHAIN_VERIFIED')).toBe('VERIFYING');
    expect(stepForEvent('RUN_COMPLETED')).toBe('COMPLETED');
    expect(stepForEvent('RUN_FAILED')).toBe('FAILED');
    expect(stepForEvent('SOMETHING_UNKNOWN')).toBeNull();
  });
});

describe('verificationReducer', () => {
  it('appends events and advances the pipeline step', () => {
    const withRun = verificationReducer(initialVerificationState, { type: 'START_BEGIN' });
    expect(withRun.starting).toBe(true);
    const after = verificationReducer(withRun, { type: 'EVENT', envelope: envelope('DISCOVERY_STARTED') });
    expect(after.logs).toHaveLength(1);
    expect(after.run?.pipeline_step ?? 'DISCOVERING').toBe('DISCOVERING');
  });

  it('caps log history', () => {
    let state = initialVerificationState;
    for (let i = 0; i < MAX_LOGS + 10; i++) {
      state = verificationReducer(state, { type: 'EVENT', envelope: envelope('DISCOVERY_PROGRESS') });
    }
    expect(state.logs).toHaveLength(MAX_LOGS);
  });
});
