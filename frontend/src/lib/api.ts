import type { Diagnostics, PreflightResult, RunDetail, RunSummary, SseEnvelope } from './types';

// Single place that knows backend routes, so path changes stay out of components.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function readJson(response: Response): Promise<never | unknown> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const detail =
      typeof body === 'object' && body !== null && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : response.statusText;
    throw new Error(detail);
  }
  return response.json() as Promise<unknown>;
}

export interface StartRunInput {
  faceImage: File | Blob;
  platform?: string;
  mode: 'profile' | 'post';
  target: string;
  consentAccepted: boolean;
  maxPosts: number;
  attest: boolean;
}

export async function startRun(input: StartRunInput): Promise<RunSummary> {
  const form = new FormData();
  form.append('face_image', input.faceImage, 'face.jpg');
  if (input.platform) form.append('platform', input.platform);
  form.append('mode', input.mode);
  form.append('target', input.target);
  form.append('consent_accepted', String(input.consentAccepted));
  form.append('max_posts', String(input.maxPosts));
  form.append('attest', String(input.attest));
  const response = await fetch(`${BASE_URL}/api/runs`, { method: 'POST', body: form });
  return (await readJson(response)) as RunSummary;
}

export async function getRun(runId: string): Promise<RunDetail> {
  const response = await fetch(`${BASE_URL}/api/runs/${runId}`);
  return (await readJson(response)) as RunDetail;
}

export async function listRuns(limit = 20): Promise<{ runs: RunSummary[] }> {
  const response = await fetch(`${BASE_URL}/api/runs?limit=${limit}`);
  return (await readJson(response)) as { runs: RunSummary[] };
}

export async function preflight(faceImage: File | Blob): Promise<PreflightResult> {
  const form = new FormData();
  form.append('face_image', faceImage, 'face.jpg');
  const response = await fetch(`${BASE_URL}/api/preflight`, { method: 'POST', body: form });
  return (await readJson(response)) as PreflightResult;
}

export async function getDiagnostics(): Promise<Diagnostics> {
  const response = await fetch(`${BASE_URL}/api/diagnostics`);
  return (await readJson(response)) as Diagnostics;
}

/** One-way SSE subscription. Callers refresh run status first on (re)connect. */
export function streamRunEvents(
  runId: string,
  onEvent: (envelope: SseEnvelope) => void,
  onError: () => void,
): () => void {
  const source = new EventSource(`${BASE_URL}/api/runs/${runId}/events`);
  source.onmessage = (message: MessageEvent) => {
    try {
      onEvent(JSON.parse(String(message.data)) as SseEnvelope);
    } catch {
      // Ignore malformed frames; status polling remains authoritative.
    }
  };
  source.onerror = () => {
    source.close();
    onError();
  };
  return () => source.close();
}

const PLATFORM_HOSTS: Record<string, string> = {
  'instagram.com': 'instagram',
  'linkedin.com': 'linkedin',
  'facebook.com': 'facebook',
  'fb.com': 'facebook',
  'reddit.com': 'reddit',
};

export function detectPlatformFromUrl(target: string): string | null {
  try {
    const host = new URL(target).hostname.toLowerCase();
    for (const [suffix, platform] of Object.entries(PLATFORM_HOSTS)) {
      if (host === suffix || host.endsWith(`.${suffix}`)) return platform;
    }
  } catch {
    return null;
  }
  return null;
}
