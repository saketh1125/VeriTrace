import { useState } from 'react';
import { CheckCircle2, ExternalLink, Loader2, XCircle } from 'lucide-react';
import { formatScore, formatTime } from '../lib/format';
import type { Candidate } from '../lib/types';

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ACCEPTED: 'border-green-300 bg-green-50 text-green-800',
    LOW_SCORE: 'border-amber-300 bg-amber-50 text-amber-800',
    NO_FACE: 'border-neutral-300 bg-neutral-100 text-neutral-600',
    MEDIA_FAILED: 'border-red-300 bg-red-50 text-red-700',
    SKIPPED: 'border-neutral-300 bg-neutral-100 text-neutral-600',
    PROCESSING: 'border-blue-300 bg-blue-50 text-blue-800',
    DISCOVERED: 'border-neutral-200 text-neutral-500',
  };
  const icon =
    status === 'ACCEPTED' ? (
      <CheckCircle2 className="h-3 w-3" />
    ) : status === 'PROCESSING' ? (
      <Loader2 className="h-3 w-3 animate-spin" />
    ) : status === 'DISCOVERED' ? null : (
      <XCircle className="h-3 w-3" />
    );
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[11px] ${styles[status] ?? styles.DISCOVERED}`}
    >
      {icon}
      {status}
    </span>
  );
}

export function CandidateExplorer({ candidates }: { candidates: Candidate[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = candidates.find((c) => c.candidate_id === selectedId) ?? null;
  if (candidates.length === 0)
    return <p className="text-sm text-neutral-500">Candidates will appear here once discovered.</p>;
  return (
    <div>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {candidates.map((candidate) => (
          <li key={candidate.candidate_id}>
            <button
              type="button"
              onClick={() => setSelectedId(candidate.candidate_id)}
              className="block w-full rounded-lg border border-neutral-200 bg-white p-2 text-left hover:border-neutral-400"
            >
              <img
                src={candidate.media_url}
                alt={`Candidate ${candidate.candidate_id}`}
                loading="lazy"
                className="mb-1 h-24 w-full rounded border object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
              <p className="font-mono text-[11px] text-neutral-500">{candidate.candidate_id}</p>
              <p className="truncate text-xs font-medium">
                {candidate.platform} · {candidate.author ?? 'unknown'}
              </p>
              <div className="mt-1 flex items-center justify-between gap-1">
                <StatusBadge status={candidate.status} />
                <span className="font-mono text-[11px]">{formatScore(candidate.face_similarity)}</span>
              </div>
            </button>
          </li>
        ))}
      </ul>

      {selected && (
        <div
          role="dialog"
          aria-label="Candidate details"
          className="fixed right-0 top-0 z-20 h-full w-full max-w-sm overflow-y-auto border-l border-neutral-200 bg-white p-4 shadow-lg"
        >
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
              Candidate details
            </h3>
            <button
              type="button"
              onClick={() => setSelectedId(null)}
              className="rounded border border-neutral-300 px-2 py-0.5 text-xs"
            >
              Close
            </button>
          </div>
          <dl className="space-y-1 text-sm">
            <div><dt className="text-xs text-neutral-500">Source</dt><dd>{selected.platform}</dd></div>
            <div><dt className="text-xs text-neutral-500">Author</dt><dd>{selected.author ?? '—'}</dd></div>
            <div>
              <dt className="text-xs text-neutral-500">Post URL</dt>
              <dd className="break-all font-mono text-xs">{selected.post_url}</dd>
            </div>
            <div><dt className="text-xs text-neutral-500">Published</dt><dd>{formatTime(selected.published_at)}</dd></div>
            <div><dt className="text-xs text-neutral-500">Faces detected</dt><dd>reported at match time</dd></div>
            <div>
              <dt className="text-xs text-neutral-500">Best face match (acceptance gate)</dt>
              <dd className="font-mono">{formatScore(selected.face_similarity)}</dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500">Image similarity (supporting signal)</dt>
              <dd className="font-mono">{formatScore(selected.image_similarity)}</dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500">Decision</dt>
              <dd><StatusBadge status={selected.status} /></dd>
            </div>
            {selected.reason && (
              <div><dt className="text-xs text-neutral-500">Reason</dt><dd className="font-mono text-xs">{selected.reason}</dd></div>
            )}
          </dl>
          <a
            href={selected.post_url}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex items-center gap-1 rounded bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white"
          >
            Open source <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      )}
    </div>
  );
}
