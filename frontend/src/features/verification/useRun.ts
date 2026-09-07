import { useEffect, useReducer, useRef } from 'react';
import { getRun, startRun, streamRunEvents, type StartRunInput } from '../../lib/api';
import {
  initialVerificationState,
  verificationReducer,
  type ConnectionState,
} from './reducer';

const MAX_RECONNECTS = 5;
const RECONNECT_DELAY_MS = 2000;

// Canonical refresh points: candidate list after discovery, full result at the
// end. Per-event updates (logs, step, progress) stay lightweight and the
// backend remains authoritative for candidates and results.
const REFRESH_EVENTS = new Set(['DISCOVERY_COMPLETED', 'RUN_COMPLETED', 'RUN_FAILED']);

export function useRun() {
  const [state, dispatch] = useReducer(verificationReducer, initialVerificationState);
  const stopRef = useRef<(() => void) | null>(null);
  const reconnectsRef = useRef(0);
  const runIdRef = useRef<string | null>(null);

  const stopStream = () => {
    stopRef.current?.();
    stopRef.current = null;
  };

  const setConnection = (connection: ConnectionState) =>
    dispatch({ type: 'CONNECTION', connection });

  const refreshStatus = async (runId: string) => {
    const run = await getRun(runId);
    dispatch({ type: 'STATUS', run });
    return run;
  };

  const connect = async (runId: string) => {
    stopStream();
    runIdRef.current = runId;
    reconnectsRef.current = 0;
    setConnection('connecting');
    try {
      const run = await refreshStatus(runId);
      if (run.status === 'COMPLETED' || run.status === 'FAILED') {
        setConnection('closed');
        return;
      }
    } catch {
      setConnection('error');
      return;
    }
    setConnection('live');
    stopRef.current = streamRunEvents(
      runId,
      (envelope) => {
        dispatch({ type: 'EVENT', envelope });
        if (REFRESH_EVENTS.has(envelope.event)) void refreshStatus(runId).catch(() => {});
      },
      () => {
        // Reconnect only after re-reading status, so missed events cannot
        // leave the UI behind.
        setConnection('reconnecting');
        window.setTimeout(() => {
          const current = runIdRef.current;
          if (!current || current !== runId) return;
          void refreshStatus(runId)
            .then((run) => {
              if (run.status === 'COMPLETED' || run.status === 'FAILED') {
                setConnection('closed');
                return;
              }
              if (reconnectsRef.current >= MAX_RECONNECTS) {
                setConnection('closed');
                return;
              }
              reconnectsRef.current += 1;
              void connect(runId);
            })
            .catch(() => setConnection('error'));
        }, RECONNECT_DELAY_MS);
      },
    );
  };

  const start = async (input: StartRunInput) => {
    stopStream();
    runIdRef.current = null;
    dispatch({ type: 'START_BEGIN' });
    try {
      const summary = await startRun(input);
      const run = await getRun(summary.run_id);
      dispatch({ type: 'START_OK', run });
      await connect(run.run_id);
    } catch (error) {
      dispatch({
        type: 'START_FAIL',
        message: error instanceof Error ? error.message : 'Failed to start run.',
      });
      setConnection('error');
    }
  };

  useEffect(() => () => stopStream(), []);

  return {
    state,
    start,
    connect,
    refresh: () => (runIdRef.current ? refreshStatus(runIdRef.current) : Promise.resolve(null)),
    clearLogs: () => dispatch({ type: 'CLEAR_LOGS' }),
  };
}
