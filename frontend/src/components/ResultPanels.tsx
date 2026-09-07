import { CheckCircle2, ExternalLink } from 'lucide-react';
import { formatScore, truncateHash } from '../lib/format';
import type { RunResult } from '../lib/types';

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-neutral-100 py-1 text-sm last:border-0">
      <dt className="shrink-0 text-xs text-neutral-500">{label}</dt>
      <dd className={`break-all text-right ${mono ? 'font-mono text-xs' : ''}`}>{value}</dd>
    </div>
  );
}

export function ResultPanels({ result }: { result: RunResult }) {
  const evidence = result.evidence;
  const chain = result.blockchain;
  const integrityOk = chain.integrity === 'VERIFIED';
  return (
    <div className="space-y-3">
      {result.outcome === 'VERIFIED' && evidence && (
        <div className="rounded-lg border border-green-300 bg-green-50 p-4">
          <p className="flex items-center gap-1 font-semibold text-green-800">
            <CheckCircle2 className="h-4 w-4" /> VERIFIED MATCH
          </p>
          <p className="text-sm text-green-800">
            {evidence.platform} · post discovered and independently face-verified
          </p>
          <dl className="mt-2">
            <Row label="Face match (gate)" value={formatScore(evidence.face_similarity)} mono />
            <Row label="Image similarity (supporting)" value={formatScore(evidence.image_similarity)} mono />
            <Row label="Evidence SHA-256" value={truncateHash(evidence.evidence_sha256, 12)} mono />
          </dl>
        </div>
      )}

      {evidence && (
        <section aria-label="Evidence" className="rounded-lg border border-neutral-200 bg-white p-4">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-neutral-500">Evidence</h3>
          <dl>
            <Row label="Source" value={`${evidence.platform}`} />
            <Row label="Post" value={evidence.post_url} mono />
            <Row label="Media SHA-256" value={truncateHash(evidence.media_sha256, 12)} mono />
            <Row label="Evidence SHA-256" value={truncateHash(evidence.evidence_sha256, 12)} mono />
            <Row label="Matching policy" value="face-threshold-v1" mono />
          </dl>
        </section>
      )}

      <section aria-label="Blockchain attestation" className="rounded-lg border border-neutral-200 bg-white p-4">
        <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Blockchain attestation
        </h3>
        <dl>
          <Row label="Network" value={`${chain.network} (${chain.chain_id})`} />
          {chain.registry && <Row label="Registry" value={truncateHash(chain.registry, 12)} mono />}
          <Row label="Evidence hash" value={truncateHash(chain.evidence_hash, 12)} mono />
          <Row label="Submission" value={chain.status} mono />
          {chain.tx_hash && <Row label="Transaction" value={truncateHash(chain.tx_hash, 12)} mono />}
        </dl>
        <div className="mt-2 space-y-0.5 text-xs">
          <p>✓ Evidence recomputed from backend record</p>
          <p>{integrityOk ? '✓' : '✗'} On-chain commitment {integrityOk ? 'matches' : `— ${chain.integrity}`}</p>
          <p className={`font-semibold ${integrityOk ? 'text-green-700' : 'text-amber-700'}`}>
            {integrityOk ? '✓ INTEGRITY VERIFIED' : `Integrity: ${chain.integrity}`}
          </p>
          <p className="text-neutral-500">
            Verification is an independent chain read, separate from submission status.
          </p>
        </div>
        {evidence && (
          <a
            href={evidence.post_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-flex items-center gap-1 rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-50"
          >
            View source <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </section>
    </div>
  );
}
