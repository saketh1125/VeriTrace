export function truncateHash(value?: string | null, head = 8): string {
  if (!value) return '—';
  return value.length > head + 3 ? `${value.slice(0, head)}…` : value;
}

export function formatScore(value?: number | null): string {
  return value === null || value === undefined || Number.isNaN(value) ? '—' : value.toFixed(3);
}

export function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString();
}

export function formatDuration(ms?: number | null): string {
  if (ms === null || ms === undefined) return '—';
  return `${(ms / 1000).toFixed(1)}s`;
}
