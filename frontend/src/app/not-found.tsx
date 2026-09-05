import Link from 'next/link';

import { PrimaryLink, SecondaryLink } from '@/components/ui/States';

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-4 text-center">
      <p className="text-sm font-medium uppercase tracking-widest text-brand-600">404</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink-900">
        We could not find that page
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-ink-500">
        The link may be out of date, or the content may have been removed by a moderator. Nothing
        here requires an account to read, so this is not a permissions problem.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <PrimaryLink href="/problems">Browse Problems</PrimaryLink>
        <SecondaryLink href="/">Go home</SecondaryLink>
      </div>
      <Link href="/search" className="mt-6 text-sm text-brand-700 hover:underline">
        Search JanDrishti instead
      </Link>
    </div>
  );
}
