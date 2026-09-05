'use client';

/**
 * Report a problem (spec 15).
 *
 * The form is fully usable before signing in — you can write the whole report,
 * attach photographs and locate it, and only meet the login prompt when you
 * press Submit. Nothing typed is lost to an authentication wall.
 */
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { ApiRequestError, api } from '@/services/api-client';
import type { Category, ProblemDetail } from '@/types/api';

interface UploadedFile {
  id: string;
  name: string;
  previewUrl: string;
}

const PRIORITIES = [
  { value: 'LOW', label: 'Low', hint: 'Inconvenient' },
  { value: 'MEDIUM', label: 'Medium', hint: 'Affects daily life' },
  { value: 'HIGH', label: 'High', hint: 'Serious disruption' },
  { value: 'CRITICAL', label: 'Critical', hint: 'Danger to life or health' },
];

export default function ReportProblemPage() {
  const router = useRouter();
  const { requireAuth } = useAuth();

  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState({
    title: '',
    description: '',
    category_id: '',
    priority: 'MEDIUM',
    address: '',
    city: '',
    district: '',
    state: '',
    pincode: '',
    is_anonymous_report: false,
  });
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    api
      .get<Category[]>('/categories/', { anonymous: true })
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  const set = (key: keyof typeof form, value: string | boolean) =>
    setForm((current) => ({ ...current, [key]: value }));

  const detectLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setCoords({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => setError('We could not read your location. You can still type the area below.'),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }, []);

  const uploadFiles = useCallback(async (fileList: FileList) => {
    setUploading(true);
    setError(null);
    for (const file of Array.from(fileList).slice(0, 10)) {
      const body = new FormData();
      body.append('file', file);
      body.append('folder', 'problems');
      try {
        const media = await api.post<{ id: string; url: string; thumbnail_url: string }>(
          '/media/upload/',
          body,
        );
        setFiles((current) => [
          ...current,
          {
            id: media.id,
            name: file.name,
            previewUrl: media.thumbnail_url || media.url || URL.createObjectURL(file),
          },
        ]);
      } catch (caught) {
        setError(
          caught instanceof ApiRequestError
            ? `${file.name}: ${caught.message}`
            : `${file.name} could not be uploaded.`,
        );
      }
    }
    setUploading(false);
  }, []);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (form.title.trim().length < 10) {
      errors.title = 'Give the problem a clear title of at least 10 characters.';
    }
    if (form.description.trim().length < 30) {
      errors.description = 'Describe the problem in at least 30 characters.';
    }
    if (!coords && !form.state.trim()) {
      errors.state = 'Add a state, or use your current location.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const submit = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      const problem = await api.post<ProblemDetail>('/problems/create/', {
        ...form,
        category_id: form.category_id || null,
        latitude: coords?.lat ?? null,
        longitude: coords?.lng ?? null,
        media_ids: files.map((file) => file.id),
      });
      router.push(`/problems/${problem.id}`);
    } catch (caught) {
      setError(
        caught instanceof ApiRequestError
          ? caught.message
          : 'Your report could not be submitted. Please try again.',
      );
      setSubmitting(false);
    }
  }, [coords, files, form, router]);

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!validate()) return;
    // Uploads already required an account, so in practice the user is signed
    // in by now — but a text-only report can reach this point anonymously.
    requireAuth(submit, { label: 'Login to submit this report', returnPath: '/report' });
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-ink-900">Report a problem</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-500">
          Describe what is wrong, where it is, and add whatever evidence you have. Reports with a
          location and photographs get routed and acted on far more often.
        </p>
      </header>

      {error && (
        <p role="alert" className="mt-6 rounded-lg bg-red-50 p-4 text-sm text-red-800">
          {error}
        </p>
      )}

      <form onSubmit={onSubmit} className="mt-8 space-y-8">
        <Field
          label="Title"
          hint="One clear sentence. e.g. Streetlight outside the primary school has been dark for weeks."
          error={fieldErrors.title}
        >
          <input
            type="text"
            required
            maxLength={200}
            value={form.title}
            onChange={(event) => set('title', event.target.value)}
            className="w-full rounded-lg border border-ink-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </Field>

        <Field
          label="What is happening?"
          hint="When did it start, who is affected, and what has been tried so far."
          error={fieldErrors.description}
        >
          <textarea
            required
            rows={6}
            maxLength={8000}
            value={form.description}
            onChange={(event) => set('description', event.target.value)}
            className="w-full rounded-lg border border-ink-300 px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </Field>

        <Field label="Category" hint="This decides which department it reaches.">
          <select
            value={form.category_id}
            onChange={(event) => set('category_id', event.target.value)}
            className="w-full rounded-lg border border-ink-300 bg-white px-3 py-2.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">Not sure — someone will categorise it</option>
            {categories.map((category) => (
              <optgroup key={category.id} label={category.name}>
                {category.children.length === 0 ? (
                  <option value={category.id}>{category.name}</option>
                ) : (
                  category.children.map((child) => (
                    <option key={child.id} value={child.id}>
                      {child.name}
                    </option>
                  ))
                )}
              </optgroup>
            ))}
          </select>
        </Field>

        <fieldset>
          <legend className="text-sm font-semibold text-ink-900">How serious is it?</legend>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {PRIORITIES.map((priority) => (
              <label
                key={priority.value}
                className={`cursor-pointer rounded-lg border px-3 py-2.5 text-center transition ${
                  form.priority === priority.value
                    ? 'border-brand-600 bg-brand-50'
                    : 'border-ink-300 hover:bg-ink-50'
                }`}
              >
                <input
                  type="radio"
                  name="priority"
                  value={priority.value}
                  checked={form.priority === priority.value}
                  onChange={(event) => set('priority', event.target.value)}
                  className="sr-only"
                />
                <span className="block text-sm font-medium text-ink-900">{priority.label}</span>
                <span className="mt-0.5 block text-xs text-ink-500">{priority.hint}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold text-ink-900">Where is it?</legend>
          <button
            type="button"
            onClick={detectLocation}
            className="mt-3 w-full rounded-lg border border-ink-300 bg-white px-4 py-2.5 text-sm font-medium text-ink-800 transition hover:bg-ink-50"
          >
            {coords
              ? `Location captured (${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)})`
              : 'Use my current location'}
          </button>
          <p className="mt-2 text-xs text-ink-400">
            Precise coordinates help group your report with others about the same spot.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input
              type="text"
              placeholder="Street or landmark"
              value={form.address}
              onChange={(event) => set('address', event.target.value)}
              className="rounded-lg border border-ink-300 px-3 py-2.5 text-sm sm:col-span-2"
            />
            <input
              type="text"
              placeholder="City"
              value={form.city}
              onChange={(event) => set('city', event.target.value)}
              className="rounded-lg border border-ink-300 px-3 py-2.5 text-sm"
            />
            <input
              type="text"
              placeholder="District"
              value={form.district}
              onChange={(event) => set('district', event.target.value)}
              className="rounded-lg border border-ink-300 px-3 py-2.5 text-sm"
            />
            <input
              type="text"
              placeholder="State"
              value={form.state}
              onChange={(event) => set('state', event.target.value)}
              aria-invalid={Boolean(fieldErrors.state)}
              className="rounded-lg border border-ink-300 px-3 py-2.5 text-sm"
            />
            <input
              type="text"
              inputMode="numeric"
              placeholder="Pincode"
              maxLength={6}
              value={form.pincode}
              onChange={(event) => set('pincode', event.target.value)}
              className="rounded-lg border border-ink-300 px-3 py-2.5 text-sm"
            />
          </div>
          {fieldErrors.state && (
            <p className="mt-1.5 text-xs text-red-700">{fieldErrors.state}</p>
          )}
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold text-ink-900">Evidence</legend>
          <p className="mt-1 text-xs text-ink-500">
            Photographs, video or documents. Uploaded files are shown as unverified until someone
            checks them.
          </p>
          <input
            type="file"
            multiple
            accept="image/*,video/*,application/pdf"
            onChange={(event) => event.target.files && void uploadFiles(event.target.files)}
            className="mt-3 block w-full text-sm text-ink-600 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-800 hover:file:bg-brand-100"
          />
          {uploading && <p className="mt-2 text-xs text-ink-500">Uploading…</p>}

          {files.length > 0 && (
            <ul className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-4">
              {files.map((file) => (
                <li key={file.id} className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={file.previewUrl}
                    alt={file.name}
                    className="aspect-square w-full rounded-lg border border-ink-200 object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => setFiles((current) => current.filter((f) => f.id !== file.id))}
                    aria-label={`Remove ${file.name}`}
                    className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-ink-900 text-xs text-white"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        <label className="flex items-start gap-3 rounded-lg border border-ink-200 bg-white p-4">
          <input
            type="checkbox"
            checked={form.is_anonymous_report}
            onChange={(event) => set('is_anonymous_report', event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
          />
          <span className="text-sm">
            <span className="font-medium text-ink-900">Report without showing my name</span>
            <span className="mt-0.5 block text-xs text-ink-500">
              Your name is hidden from the public page. Your account is still recorded internally
              for moderation, so this is not anonymity from JanDrishti itself.
            </span>
          </span>
        </label>

        <div className="flex flex-col gap-3 border-t border-ink-200 pt-6 sm:flex-row sm:items-center">
          <button
            type="submit"
            disabled={submitting || uploading}
            className="rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60"
          >
            {submitting ? 'Submitting…' : 'Submit report'}
          </button>
          <Link href="/problems" className="text-sm text-ink-500 hover:text-ink-800">
            Cancel
          </Link>
          <p className="text-xs text-ink-400 sm:ml-auto">
            You will be asked to sign in when you submit.
          </p>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-ink-900">{label}</label>
      {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
      <div className="mt-2">{children}</div>
      {error && (
        <p role="alert" className="mt-1.5 text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
