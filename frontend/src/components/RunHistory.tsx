import { useEffect, useState } from 'react';
import { listRuns } from '../lib/api';
import { formatDuration, formatTime } from '../lib/format';
import type { RunSummary } from '../lib/types';

export function RunHistory({
  onSelect,
  onClose,
}: {
  onSelect: (runId: string) => void;
  onClose: () => void;
}) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then((result) => setRuns(result.runs))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load runs.'));
  }, []);

  return (
    <div role="dialog" aria-label="Run history" className="fixed right-0 top-0 z-20 h-full w-full max-w-sm overflow-y-auto border-l border-neutral-200 bg-white p-4 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Recent runs</h3>
        <button type="button" onClick={onClose} className="rounded border border-neutral-300 px-2 py-0.5 text-xs">
          Close
        </button>
      </div>
      {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
      {runs.length === 0 && !error && <p className="text-sm text-neutral-500">No runs yet.</p>}
      <ul className="space-y-1">
        {runs.map((run) => (
          <li key={run.run_id}>
            <button
              type="button"
              onClick={() => {
                onSelect(run.run_id);
                onClose();
              }}
              className="block w-full rounded border border-neutral-200 px-2 py-1.5 text-left hover:border-neutral-400"
            >
              <p className="font-mono text-xs">{run.run_id}</p>
              <p className="text-xs text-neutral-600">
                {run.status} · {run.outcome ?? run.error_code ?? run.pipeline_step} ·{' '}
                {formatTime(run.created_at)} · {formatDuration(run.duration_ms)}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
