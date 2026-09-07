import { Activity } from 'lucide-react';
import type { Diagnostics } from '../lib/types';

interface Props {
  diagnostics: Diagnostics | null;
  apiReachable: boolean;
  onOpenDiagnostics: () => void;
  onOpenHistory: () => void;
}

function Dot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-neutral-600">
      <span
        className={`inline-block h-2 w-2 rounded-full ${ok ? 'bg-green-600' : 'bg-neutral-300'}`}
        aria-hidden
      />
      {label}
    </span>
  );
}

export function Header({ diagnostics, apiReachable, onOpenDiagnostics, onOpenHistory }: Props) {
  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">VERITRACE</h1>
          <p className="text-xs text-neutral-500">
            Face-to-content verification with tamper-evident provenance
          </p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <Dot ok={apiReachable} label="API" />
          <Dot ok={diagnostics?.apify.configured ?? false} label="APIFY" />
          <Dot ok={diagnostics !== null} label={`FACE ${diagnostics?.face.model ?? ''}`.trim()} />
          <Dot
            ok={(diagnostics?.blockchain.registry_configured ?? false) && apiReachable}
            label="CHAIN"
          />
          <button
            type="button"
            onClick={onOpenHistory}
            className="rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-50"
          >
            Runs
          </button>
          <button
            type="button"
            onClick={onOpenDiagnostics}
            className="rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-50"
            aria-label="Open diagnostics"
          >
            <Activity className="inline h-3.5 w-3.5" /> Settings
          </button>
        </div>
      </div>
    </header>
  );
}
