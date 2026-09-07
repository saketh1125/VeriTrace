import { useEffect, useRef, useState } from 'react';
import { formatTime } from '../lib/format';
import type { SseEnvelope } from '../lib/types';

interface Props {
  logs: SseEnvelope[];
  connected: boolean;
  onClear: () => void;
}

const LEVELS = ['INFO', 'WARN', 'ERROR'] as const;

export function LogTerminal({ logs, connected, onClear }: Props) {
  const [paused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [visible, setVisible] = useState<Set<string>>(new Set(LEVELS));
  const [expanded, setExpanded] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll && !paused) bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [logs, autoScroll, paused]);

  const shown = paused ? logs : logs;
  const filtered = shown.filter((entry) => visible.has(entry.level));

  const toggle = (level: string) =>
    setVisible((old) => {
      const next = new Set(old);
      if (next.has(level)) next.delete(level);
      else next.add(level);
      return next;
    });

  const copy = () => {
    const text = filtered
      .map((e) => `${e.timestamp} ${e.level} ${e.event} ${JSON.stringify(e.data)}`)
      .join('\n');
    void navigator.clipboard?.writeText(text).catch(() => {});
  };

  const levelColor = (level: string) =>
    level === 'ERROR' ? 'text-red-600' : level === 'WARN' ? 'text-amber-600' : 'text-green-700';

  return (
    <section aria-label="Live logs" className="rounded-lg border border-neutral-200 bg-white">
      <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 px-3 py-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Live logs</h2>
        <span className="text-xs text-neutral-500">
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
        <div className="ml-auto flex items-center gap-1 text-xs">
          {LEVELS.map((level) => (
            <label key={level} className="inline-flex items-center gap-1 border border-neutral-200 px-1.5 py-0.5">
              <input type="checkbox" checked={visible.has(level)} onChange={() => toggle(level)} />
              {level}
            </label>
          ))}
          <button type="button" onClick={onClear} className="rounded border border-neutral-300 px-1.5 py-0.5">Clear</button>
          <button type="button" onClick={copy} className="rounded border border-neutral-300 px-1.5 py-0.5">Copy</button>
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            className="rounded border border-neutral-300 px-1.5 py-0.5"
          >
            {paused ? 'Resume' : 'Pause'}
          </button>
          <label className="inline-flex items-center gap-1">
            <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
            Auto-scroll
          </label>
        </div>
      </div>
      <ol className="h-56 overflow-y-auto bg-neutral-950 p-2 font-mono text-[11px] leading-5 text-neutral-200">
        {filtered.map((entry, index) => (
          <li key={`${entry.timestamp}-${index}`}>
            <button
              type="button"
              onClick={() => setExpanded(expanded === index ? null : index)}
              className="block w-full truncate text-left hover:bg-neutral-900"
            >
              <span className="text-neutral-500">{formatTime(entry.timestamp)}</span>{' '}
              <span className={levelColor(entry.level)}>{entry.level}</span>{' '}
              <span className="text-sky-300">{entry.event}</span>{' '}
              <span className="text-neutral-400">
                {entry.candidate_id ? `${entry.candidate_id} ` : ''}
                {summarize(entry)}
              </span>
            </button>
            {expanded === index && (
              <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-neutral-900 p-2 text-neutral-300">
                {JSON.stringify(entry, null, 2)}
              </pre>
            )}
          </li>
        ))}
        <div ref={bottomRef} />
      </ol>
    </section>
  );
}

function summarize(entry: SseEnvelope): string {
  const data = entry.data;
  if (typeof data.score === 'number') return `score=${data.score}`;
  if (typeof data.discovered === 'number') return `discovered=${data.discovered}`;
  if (typeof data.evidence_sha256 === 'string')
    return `evidence=${String(data.evidence_sha256).slice(0, 12)}…`;
  if (typeof data.code === 'string') return String(data.code);
  if (typeof data.outcome === 'string') return String(data.outcome);
  if (typeof data.integrity === 'string') return String(data.integrity);
  return '';
}
