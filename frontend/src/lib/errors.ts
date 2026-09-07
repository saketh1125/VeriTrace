// User-facing copy for every backend failure code in the UI contract.
// Components render these strings; they never invent their own meanings.

const MESSAGES: Record<string, string> = {
  CONSENT_REQUIRED: 'Consent is required before verification starts.',
  UNSUPPORTED_CONSENT_VERSION: 'This consent version is not supported.',
  TARGET_REQUIRED: 'Enter a username, profile URL, or post URL.',
  PROFILE_TARGET_REQUIRED: 'Profile mode needs a username or profile URL.',
  POST_URL_REQUIRED: 'Post mode needs a direct public post URL.',
  UNSUPPORTED_PLATFORM: 'That platform is not supported.',
  INPUT_INVALID: 'That file is not a readable JPG, PNG, or WEBP image.',
  NO_FACE_FOUND: 'No usable face detected. Upload a clear, front-facing photo.',
  MULTIPLE_FACES:
    'VeriTrace requires one usable face in the input image. Retake or upload a single-person image.',
  FACE_QUALITY_LOW: 'The face is too small or unclear. Use a larger, well-lit photo.',
  FACE_MATCH_LOW: 'Candidate rejected: face similarity below threshold.',
  NO_FACE_IN_MEDIA: 'No usable face found in this candidate media.',
  MEDIA_FETCH_FAILED: 'Candidate media could not be downloaded.',
  DISCOVERY_PROVIDER_ERROR: 'Discovery failed at the provider. See run logs; no match was decided.',
  NO_CANDIDATES: 'Discovery completed with zero candidates.',
  NO_VERIFIED_CANDIDATE: 'Search completed. No candidate passed face verification.',
  BLOCKCHAIN_SUBMISSION_FAILED: 'Face verification stands, but blockchain attestation failed.',
  BLOCKCHAIN_NOT_CONFIGURED: 'Blockchain is not configured on this host. Verification result kept.',
  BLOCKCHAIN_RECORD_NOT_FOUND: 'No on-chain commitment found for this evidence hash.',
  INTEGRITY_MISMATCH: 'Warning: recomputed evidence differs from the on-chain commitment.',
  TAMPERED: 'Warning: recomputed evidence differs from the on-chain commitment.',
  RUN_NOT_FOUND: 'Run not found. It may have expired from local history.',
};

export function errorMessage(code?: string | null): string {
  if (!code) return 'Something went wrong.';
  return MESSAGES[code] ?? code;
}
