import { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, Upload } from 'lucide-react';
import { detectPlatformFromUrl, preflight } from '../lib/api';
import { errorMessage } from '../lib/errors';
import type { PreflightResult } from '../lib/types';

export interface RequestValues {
  faceImage: File | null;
  platform: string;
  mode: 'profile' | 'post';
  target: string;
  maxPosts: number;
  attest: boolean;
  consent: boolean;
}

interface Props {
  starting: boolean;
  startError: string | null;
  onStart: (values: RequestValues) => void;
}

const PLATFORMS = ['instagram', 'linkedin', 'facebook', 'reddit'];

export function RequestForm({ starting, startError, onStart }: Props) {
  const [faceImage, setFaceImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [platform, setPlatform] = useState('instagram');
  const [mode, setMode] = useState<'profile' | 'post'>('profile');
  const [target, setTarget] = useState('');
  const [maxPosts, setMaxPosts] = useState(30);
  const [attest, setAttest] = useState(true);
  const [consent, setConsent] = useState(false);
  const [check, setCheck] = useState<PreflightResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, [previewUrl]);

  const runPreflight = async (file: File) => {
    setChecking(true);
    try {
      setCheck(await preflight(file));
    } catch (error) {
      setCheck({ ok: false, error_code: 'INPUT_INVALID', message: String(error) });
    } finally {
      setChecking(false);
    }
  };

  const adoptFile = (file: File) => {
    setFaceImage(file);
    setPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(file);
    });
    setCheck(null);
    void runPreflight(file);
  };

  const onTargetChange = (value: string) => {
    setTarget(value);
    const detected = detectPlatformFromUrl(value);
    if (detected && detected !== platform) setPlatform(detected);
    if (/^https?:\/\//i.test(value)) setMode('post');
  };

  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      setCameraOn(true);
      requestAnimationFrame(() => {
        if (videoRef.current) videoRef.current.srcObject = stream;
      });
    } catch {
      setCheck({ ok: false, error_code: 'INPUT_INVALID', message: 'Camera unavailable.' });
    }
  };

  const captureFrame = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      setCameraOn(false);
      if (blob) adoptFile(new File([blob], 'camera.jpg', { type: 'image/jpeg' }));
    }, 'image/jpeg');
  };

  const valid = faceImage && check?.ok && target.trim() !== '' && consent && !checking;
  const inputClass =
    'w-full rounded border border-neutral-300 px-2 py-1.5 text-sm focus:border-neutral-500 focus:outline-none';

  return (
    <section aria-label="Verification request" className="rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">Request</h2>

      <label className="mb-1 block text-sm font-medium" htmlFor="face-input">
        Face image
      </label>
      <div className="mb-2 flex items-center gap-2">
        <label
          htmlFor="face-input"
          className="inline-flex cursor-pointer items-center gap-1 rounded border border-neutral-300 px-2 py-1.5 text-sm hover:bg-neutral-50"
        >
          <Upload className="h-4 w-4" /> Upload
        </label>
        <button
          type="button"
          onClick={() => (cameraOn ? captureFrame() : void openCamera())}
          className="inline-flex items-center gap-1 rounded border border-neutral-300 px-2 py-1.5 text-sm hover:bg-neutral-50"
        >
          <Camera className="h-4 w-4" /> {cameraOn ? 'Capture frame' : 'Camera'}
        </button>
        <input
          id="face-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) adoptFile(file);
          }}
        />
      </div>
      {cameraOn && <video ref={videoRef} autoPlay playsInline className="mb-2 w-full rounded border" />}
      {previewUrl && (
        <img src={previewUrl} alt="Face input preview" className="mb-2 h-32 w-32 rounded border object-cover" />
      )}
      <div className="mb-3 text-xs" role="status">
        {checking && (
          <span className="inline-flex items-center gap-1 text-neutral-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking face…
          </span>
        )}
        {!checking && check?.ok && <span className="text-green-700">One usable face detected.</span>}
        {!checking && check && !check.ok && (
          <span className="text-red-700">{check.message ?? errorMessage(check.error_code)}</span>
        )}
      </div>

      <div className="mb-2 grid grid-cols-2 gap-2">
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="platform">
            Platform
          </label>
          <select
            id="platform"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className={inputClass}
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p[0].toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <span className="mb-1 block text-sm font-medium">Mode</span>
          <div className="flex gap-3 pt-1.5 text-sm">
            <label className="inline-flex items-center gap-1">
              <input type="radio" checked={mode === 'profile'} onChange={() => setMode('profile')} /> Profile
            </label>
            <label className="inline-flex items-center gap-1">
              <input type="radio" checked={mode === 'post'} onChange={() => setMode('post')} /> Post
            </label>
          </div>
        </div>
      </div>

      <label className="mb-1 block text-sm font-medium" htmlFor="target">
        Target
      </label>
      <input
        id="target"
        value={target}
        onChange={(e) => onTargetChange(e.target.value)}
        placeholder={mode === 'post' ? 'https://… public post URL' : '@username or profile URL'}
        className={`${inputClass} mb-2 font-mono`}
      />

      <div className="mb-2 flex items-center gap-4 text-sm">
        <label className="inline-flex items-center gap-1" title="Bounded inspection limit for profile mode">
          Limit
          <input
            type="number"
            min={1}
            max={50}
            value={maxPosts}
            onChange={(e) => setMaxPosts(Number(e.target.value) || 30)}
            className="w-16 rounded border border-neutral-300 px-1 py-0.5"
          />
        </label>
        <label className="inline-flex items-center gap-1">
          <input type="checkbox" checked={attest} onChange={(e) => setAttest(e.target.checked)} /> Attest on-chain
        </label>
      </div>

      <label className="mb-3 flex items-start gap-2 text-xs text-neutral-700">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5"
        />
        I consent to local face processing and understand this establishes face-content
        correspondence only — not identity, authorship, or ownership.
      </label>

      {startError && (
        <p role="alert" className="mb-2 rounded border border-red-300 bg-red-50 px-2 py-1 text-xs text-red-700">
          {errorMessage(startError)}
        </p>
      )}

      <button
        type="button"
        disabled={!valid || starting}
        onClick={() => faceImage && onStart({ faceImage, platform, mode, target, maxPosts, attest, consent })}
        className="w-full rounded bg-neutral-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
      >
        {starting ? 'Starting…' : 'Verify'}
      </button>
    </section>
  );
}
