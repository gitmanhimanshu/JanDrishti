'use client';

/**
 * Filter sidebar.
 *
 * Filters are URL state, not component state: a filtered view can be shared,
 * bookmarked and indexed, and the back button behaves the way a reader expects.
 */
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useState } from 'react';

import type { Category } from '@/types/api';

const STATUS_GROUPS = [
  { value: 'SUBMITTED', label: 'Newly reported' },
  { value: 'DEPARTMENT_ASSIGNED', label: 'With a department' },
  { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
  { value: 'WORK_IN_PROGRESS', label: 'Work in progress' },
  { value: 'RESOLVED', label: 'Resolved' },
];

const PRIORITIES = [
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

export function ProblemFilters({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isOpen, setIsOpen] = useState(false);
  const [locating, setLocating] = useState(false);

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) params.set(key, value);
      else params.delete(key);
      // Any filter change invalidates the current page number.
      params.delete('page');
      router.push(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams],
  );

  const useMyLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('tab', 'nearby');
        params.set('lat', position.coords.latitude.toFixed(6));
        params.set('lng', position.coords.longitude.toFixed(6));
        params.delete('page');
        router.push(`${pathname}?${params.toString()}`);
        setLocating(false);
      },
      // Declining location is a legitimate choice, not an error to shout about.
      () => setLocating(false),
      { timeout: 8000 },
    );
  }, [pathname, router, searchParams]);

  const activeCount = ['q', 'category', 'state', 'status', 'priority'].filter((key) =>
    searchParams.get(key),
  ).length;

  return (
    <aside className="lg:sticky lg:top-24 lg:h-fit">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        className="mb-4 flex w-full items-center justify-between rounded-lg border border-ink-300 bg-white px-4 py-2.5 text-sm font-medium text-ink-800 lg:hidden"
      >
        Filters{activeCount > 0 ? ` (${activeCount})` : ''}
        <span aria-hidden="true">{isOpen ? '−' : '+'}</span>
      </button>

      <div className={`${isOpen ? 'block' : 'hidden'} space-y-6 lg:block`}>
        <div>
          <label htmlFor="filter-search" className="block text-sm font-semibold text-ink-900">
            Search
          </label>
          <input
            id="filter-search"
            type="search"
            defaultValue={searchParams.get('q') ?? ''}
            placeholder="Road, water, hospital…"
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                setParam('q', (event.target as HTMLInputElement).value.trim() || null);
              }
            }}
            className="mt-2 w-full rounded-lg border border-ink-300 px-3 py-2 text-sm placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div>
          <label htmlFor="filter-category" className="block text-sm font-semibold text-ink-900">
            Category
          </label>
          <select
            id="filter-category"
            value={searchParams.get('category') ?? ''}
            onChange={(event) => setParam('category', event.target.value || null)}
            className="mt-2 w-full rounded-lg border border-ink-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <optgroup key={category.id} label={category.name}>
                <option value={category.id}>All {category.name}</option>
                {category.children.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filter-state" className="block text-sm font-semibold text-ink-900">
            State
          </label>
          <input
            id="filter-state"
            type="text"
            defaultValue={searchParams.get('state') ?? ''}
            placeholder="e.g. Maharashtra"
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                setParam('state', (event.target as HTMLInputElement).value.trim() || null);
              }
            }}
            className="mt-2 w-full rounded-lg border border-ink-300 px-3 py-2 text-sm placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <fieldset>
          <legend className="text-sm font-semibold text-ink-900">Status</legend>
          <div className="mt-2 space-y-1.5">
            {STATUS_GROUPS.map((status) => (
              <label key={status.value} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="status"
                  checked={searchParams.get('status') === status.value}
                  onChange={() => setParam('status', status.value)}
                  className="h-4 w-4 border-ink-300 text-brand-600 focus:ring-brand-500"
                />
                <span className="text-ink-600">{status.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-sm font-semibold text-ink-900">Priority</legend>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {PRIORITIES.map((priority) => {
              const isActive = searchParams.get('priority') === priority.value;
              return (
                <button
                  key={priority.value}
                  type="button"
                  onClick={() => setParam('priority', isActive ? null : priority.value)}
                  aria-pressed={isActive}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    isActive
                      ? 'border-brand-600 bg-brand-50 text-brand-800'
                      : 'border-ink-300 text-ink-600 hover:bg-ink-50'
                  }`}
                >
                  {priority.label}
                </button>
              );
            })}
          </div>
        </fieldset>

        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="w-full rounded-lg border border-ink-300 bg-white px-4 py-2.5 text-sm font-medium text-ink-800 transition hover:bg-ink-50 disabled:opacity-60"
        >
          {locating ? 'Finding you…' : 'Show problems near me'}
        </button>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={() => router.push(pathname)}
            className="w-full text-sm font-medium text-brand-700 hover:underline"
          >
            Clear all filters
          </button>
        )}
      </div>
    </aside>
  );
}
