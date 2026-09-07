import { useCallback, useEffect, useState } from 'react';
import { getDiagnostics } from '../lib/api';
import { errorMessage } from '../lib/errors';
import { formatDuration, truncateHash } from '../lib/format';
import type { Diagnostics, PipelineStep, RunDetail } from '../lib/types';
import { CandidateExplorer } from '../components/CandidateExplorer';
import { DiagnosticsDrawer } from '../components/DiagnosticsDrawer';
import { Header } from '../components/Header';
import { LogTerminal } from '../components/LogTerminal';
import { PipelineStepper } from '../components/PipelineStepper';
import { RequestForm, type RequestValues } from '../components/RequestForm';
import { ResultPanels } from '../components/ResultPanels';
import { RunHistory } from '../components/RunHistory';
import { useRun } from '../features/verification/useRun';

function stepDetail(step: PipelineStep, run: RunDetail): string | null {
  switch (step) {
    case 'DISCOVERING':
      return `${run.candidate_count} candidates discovered`;
    case 'FETCHING_MEDIA':
    case 'MATCHING':
      return `${run.processed_count} / ${run.candidate_count} candidates processed`;
    case 'BUILDING_EVIDENCE':
      return run.result?.evidence?.evidence_sha256
        ? `evidence ${run.result.evidence.evidence_sha256}`
        : null;
    case 'ATTESTING':
    case 'VERIFYING':
      return run.result
        ? `${run.result.blockchain.status} · integrity ${run.result.blockchain.integrity}`
        : null;
    default:
      return null;
  }
}

export function App() {
  const { state, start, connect, clearLogs } = useRun();
  const { run, logs, connection, starting, startError } = state;
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [apiReachable, setApiReachable] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedStep, setSelectedStep] = useState<PipelineStep | null>(null);

  useEffect(() => {
    getDiagnostics()
      .then((result) => {
        setDiagnostics(result);
        setApiReachable(true);
      })
      .catch(() => setApiReachable(false));
  }, []);

  const handleStart = useCallback(
    (values: RequestValues) => {
      if (!values.faceImage) return;
      void start({
        faceImage: values.faceImage,
        platform: values.platform,
        mode: values.mode,
        target: values.target,
        consentAccepted: values.consent,
        maxPosts: values.maxPosts,
        attest: values.attest,
      });
    },
    [start],
  );

  const failed = run?.status === 'FAILED';
  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <Header
        diagnostics={diagnostics}
        apiReachable={apiReachable}
        onOpenDiagnostics={() => setShowDiagnostics(true)}
        onOpenHistory={() => setShowHistory(true)}
      />
      <main className="mx-auto max-w-6xl space-y-3 px-4 py-4">
        {run && failed && (
          <p role="alert" className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
            {errorMessage(run.error_code)} {run.error_message ? `(${run.error_message})` : ''}
          </p>
        )}
        <div className="grid gap-3 lg:grid-cols-[340px_1fr]">
          <RequestForm starting={starting} startError={startError} onStart={handleStart} />
          <div className="space-y-3">
            <section aria-label="Pipeline" className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Pipeline</h2>
                {run && (
                  <p className="font-mono text-xs text-neutral-500">
                    {run.run_id} · {run.platform} · {run.method} · {run.processed_count}/{run.candidate_count} ·{' '}
                    {formatDuration(run.duration_ms)} · {connection}
                  </p>
                )}
              </div>
              <PipelineStepper
                current={run?.pipeline_step ?? 'IDLE'}
                failed={failed}
                detail={run && selectedStep ? stepDetail(selectedStep, run) : null}
                selected={selectedStep}
                onSelect={setSelectedStep}
              />
            </section>
            <section aria-label="Candidates" className="rounded-lg border border-neutral-200 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Candidates / Result
              </h2>
              <CandidateExplorer candidates={run?.candidates ?? []} />
            </section>
            {run?.result && (
              <ResultPanels result={run.result} />
            )}
            {run?.result?.evidence && (
              <p className="font-mono text-[11px] text-neutral-400">
                evidence {truncateHash(run.result.evidence.evidence_sha256, 16)}
              </p>
            )}
          </div>
        </div>
        <LogTerminal
          logs={logs}
          connected={connection === 'live'}
          onClear={clearLogs}
        />
      </main>
      {showDiagnostics && (
        <DiagnosticsDrawer diagnostics={diagnostics} onClose={() => setShowDiagnostics(false)} />
      )}
      {showHistory && (
        <RunHistory onSelect={(runId) => void connect(runId)} onClose={() => setShowHistory(false)} />
      )}
    </div>
  );
}
