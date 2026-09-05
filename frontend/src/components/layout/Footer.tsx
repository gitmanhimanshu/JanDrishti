import Image from 'next/image';
import Link from 'next/link';

import { WhatsAppMark } from '@/features/community/WhatsAppInvite';
import { WHATSAPP_INVITE_URL } from '@/lib/community';

const COLUMNS = [
  {
    heading: 'Explore',
    links: [
      { href: '/problems', label: 'Problems' },
      { href: '/experience', label: 'Experience & Ideas' },
      { href: '/projects', label: 'Projects' },
      { href: '/impact', label: 'Impact' },
    ],
  },
  {
    heading: 'Discover',
    links: [
      { href: '/departments', label: 'Departments' },
      { href: '/states', label: 'States' },
      { href: '/search', label: 'Search' },
    ],
  },
  {
    heading: 'About',
    links: [
      { href: '/how-it-works', label: 'How It Works' },
      { href: '/about', label: 'About JanDrishti' },
      { href: '/about/privacy', label: 'Privacy' },
      { href: '/about/moderation', label: 'Moderation policy' },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-ink-200 bg-white">

      <div className="mx-auto max-w-content px-4 py-12 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-2.5">
              <Image
                src="/logo-mark.png"
                alt=""
                width={36}
                height={36}
                className="h-9 w-9 object-contain"
              />
              <span className="text-base font-bold tracking-tight">
                <span className="text-brand-900">Jan</span>
                <span className="text-leaf-800">Drishti</span>
              </span>
            </div>

            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.16em]">
              <span className="text-brand-500">See.</span>{' '}
              <span className="text-saffron-600">Suggest.</span>{' '}
              <span className="text-leaf-600">Solve.</span>
            </p>

            <a
              href={WHATSAPP_INVITE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-leaf-200 bg-leaf-50 px-3 py-2 text-xs font-semibold text-leaf-800 transition hover:bg-leaf-100"
            >
              <WhatsAppMark className="h-4 w-4" />
              Join the community on WhatsApp
            </a>

            <p className="mt-4 max-w-xs text-sm leading-relaxed text-ink-500">
              Public problems, real evidence, professional experience and transparent progress
              — brought together so communities can see what matters and help move it forward.
            </p>
          </div>

          {COLUMNS.map((column) => (
            <nav key={column.heading} aria-label={column.heading}>
              <p className="text-sm font-semibold text-brand-900">{column.heading}</p>
              <ul className="mt-3 space-y-2">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-500 transition hover:text-brand-700"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-ink-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-3xl text-xs leading-relaxed text-ink-400">
            Content on JanDrishti is contributed by the public. A verification badge confirms a
            professional claim; it is not an endorsement of any particular statement. Evidence
            marked as uploaded has not been independently verified.
          </p>
          <p className="shrink-0 text-xs font-semibold uppercase tracking-[0.18em] text-ink-400">
            It&rsquo;s our India · Let&rsquo;s improve it
          </p>
        </div>
      </div>
    </footer>
  );
}
