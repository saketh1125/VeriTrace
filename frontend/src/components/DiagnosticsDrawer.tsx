import type { Diagnostics } from '../lib/types';

export function DiagnosticsDrawer({
  diagnostics,
  onClose,
}: {
  diagnostics: Diagnostics | null;
  onClose: () => void;
}) {
  return (
    <div role="dialog" aria-label="Diagnostics" className="fixed right-0 top-0 z-20 h-full w-full max-w-sm overflow-y-auto border-l border-neutral-200 bg-white p-4 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Diagnostics</h3>
        <button type="button" onClick={onClose} className="rounded border border-neutral-300 px-2 py-0.5 text-xs">
          Close
        </button>
      </div>
      {!diagnostics ? (
        <p className="text-sm text-neutral-500">Diagnostics unavailable.</p>
      ) : (
        <dl className="space-y-1 font-mono text-xs">
          <Row label="Face model" value={diagnostics.face.model} />
          <Row label="Detection size" value={diagnostics.face.detection_size.join('×')} />
          <Row label="Min detection score" value={String(diagnostics.face.min_detection_score)} />
          <Row label="Min face size" value={`${diagnostics.face.min_face_size}px`} />
          <Row label="Face match threshold" value={String(diagnostics.face.match_threshold)} />
          <Row label="Discovery limit" value={String(diagnostics.discovery.default_limit)} />
          <Row label="Blockchain" value={`${diagnostics.blockchain.network} (${diagnostics.blockchain.chain_id})`} />
          <Row label="Apify key" value={diagnostics.apify.configured ? 'configured' : 'not configured'} />
          <Row label="Registry" value={diagnostics.blockchain.registry_configured ? 'configured' : 'not configured'} />
          <Row label="Debug logging" value="OFF" />
        </dl>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 border-b border-neutral-100 py-1">
      <dt className="text-neutral-500">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
