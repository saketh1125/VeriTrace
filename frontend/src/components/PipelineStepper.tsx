import { AlertTriangle, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import type { PipelineStep } from '../lib/types';

const STEPS: { step: PipelineStep; label: string }[] = [
  { step: 'VALIDATING_INPUT', label: 'Consent' },
  { step: 'PROCESSING_FACE', label: 'Face' },
  { step: 'DISCOVERING', label: 'Discovery' },
  { step: 'FETCHING_MEDIA', label: 'Media' },
  { step: 'MATCHING', label: 'Match' },
  { step: 'BUILDING_EVIDENCE', label: 'Evidence' },
  { step: 'ATTESTING', label: 'Blockchain' },
  { step: 'VERIFYING', label: 'Verify' },
];

interface Props {
  current: PipelineStep;
  failed: boolean;
  detail: string | null;
  selected: PipelineStep | null;
  onSelect: (step: PipelineStep | null) => void;
}

export function PipelineStepper({ current, failed, detail, selected, onSelect }: Props) {
  if (current === 'IDLE')
    return <p className="text-sm text-neutral-500">No run yet. Configure a request and press Verify.</p>;
  const order = (step: PipelineStep) => STEPS.findIndex((s) => s.step === step);
  const currentIndex = current === 'COMPLETED' ? STEPS.length : order(current);
  return (
    <div>
      <ol className="flex flex-wrap gap-1">
        {STEPS.map(({ step, label }, index) => {
          const done = index < currentIndex || current === 'COMPLETED';
          const isCurrent = step === current && !failed && current !== 'COMPLETED';
          const isFailed = step === current && failed;
          return (
            <li key={step}>
              <button
                type="button"
                onClick={() => onSelect(selected === step ? null : step)}
                className={`flex items-center gap-1 rounded border px-2 py-1 text-xs ${
                  isFailed
                    ? 'border-red-400 bg-red-50 text-red-700'
                    : isCurrent
                      ? 'border-neutral-900 bg-neutral-900 text-white'
                      : done
                        ? 'border-green-300 bg-green-50 text-green-800'
                        : 'border-neutral-200 text-neutral-400'
                }`}
                aria-current={isCurrent ? 'step' : undefined}
              >
                {isFailed ? (
                  <XCircle className="h-3.5 w-3.5" />
                ) : done ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : isCurrent ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <span className="inline-block h-3.5 w-3.5 text-center">○</span>
                )}
                {label}
              </button>
            </li>
          );
        })}
      </ol>
      {current === 'COMPLETED' && (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-green-700">
          <CheckCircle2 className="h-3.5 w-3.5" /> COMPLETED
        </p>
      )}
      {failed && (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-red-700">
          <AlertTriangle className="h-3.5 w-3.5" /> FAILED at {current}
        </p>
      )}
      {selected && detail && (
        <p className="mt-2 rounded border border-neutral-200 bg-neutral-50 px-2 py-1 font-mono text-xs text-neutral-700">
          {detail}
        </p>
      )}
    </div>
  );
}
