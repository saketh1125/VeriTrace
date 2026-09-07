import { describe, expect, it } from 'vitest';
import { errorMessage } from './errors';

// Every failure code in the UI contract must have user-facing copy.
const CONTRACT_CODES = [
  'CONSENT_REQUIRED',
  'NO_FACE_FOUND',
  'MULTIPLE_FACES',
  'FACE_QUALITY_LOW',
  'DISCOVERY_PROVIDER_ERROR',
  'NO_CANDIDATES',
  'MEDIA_FETCH_FAILED',
  'FACE_MATCH_LOW',
  'NO_VERIFIED_CANDIDATE',
  'BLOCKCHAIN_SUBMISSION_FAILED',
  'INTEGRITY_MISMATCH',
  'TAMPERED',
  'BLOCKCHAIN_RECORD_NOT_FOUND',
];

describe('errorMessage', () => {
  it('covers every locked failure state', () => {
    for (const code of CONTRACT_CODES) {
      expect(errorMessage(code), code).not.toBe(code);
    }
  });

  it('falls back gracefully', () => {
    expect(errorMessage(null)).toBe('Something went wrong.');
    expect(errorMessage('BRAND_NEW_CODE')).toBe('BRAND_NEW_CODE');
  });
});
