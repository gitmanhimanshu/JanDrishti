'use client';

/**
 * Sticky, responsive navbar (spec 10).
 *
 * The right-hand side differs for anonymous and signed-in visitors, but the
 * navigation itself never does: browsing is the same for everyone, which is the
 * whole public-first premise.
 */
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAuth } from '@/features/authentication/auth-context';
import { NotificationBell } from '@/features/notifications/NotificationBell';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/problems', label: 'Problems' },
  { href: '/experience', label: 'Experience & Ideas' },
  { href: '/projects', label: 'Projects' },
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/about', label: 'About' },
];

const DISCOVERY_LINKS = [
  { href: '/departments', label: 'Departments' },
  { href: '/states', label: 'States' },
  { href: '/impact', label: 'Impact' },
];

export function Navbar() {
  const pathname = usePathname();
  const { user, isLoading, requireAuth, signOut } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // A route change should never leave the drawer hanging open behind the new
  // page.
  useEffect(() => {
    setIsMenuOpen(false);
  }, [pathname]);

  const openLogin = () =>
    requireAuth(() => undefined, {
      label: 'Sign in to JanDrishti',
      returnPath: pathname,
    });

  return (
    <header className="sticky top-0 z-40 border-b border-ink-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-content items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="JanDrishti home">
          <Image
            src="/logo-mark.png"
            alt=""
            width={40}
            height={40}
            priority
            className="h-10 w-10 object-contain"
          />
          <span className="flex flex-col leading-none">
            <span className="text-[18px] font-bold tracking-tight">
              {/* The wordmark itself is two-tone: navy Jan, green Drishti. */}
              <span className="text-brand-900">Jan</span>
              <span className="text-leaf-800">Drishti</span>
            </span>
            <span className="mt-1 hidden text-[10px] font-semibold uppercase tracking-[0.16em] sm:block">
              <span className="text-brand-500">See.</span>{' '}
              <span className="text-saffron-600">Suggest.</span>{' '}
              <span className="text-leaf-600">Solve.</span>
            </span>
          </span>
        </Link>

        <nav aria-label="Main" className="ml-4 hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => {
            // '/' is a prefix of every route, so Home needs an exact match
            // or it would light up on every page.
            const isActive =
              link.href === '/' ? pathname === '/' : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive ? 'page' : undefined}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-brand-50 text-brand-800'
                    : 'text-ink-600 hover:bg-ink-50 hover:text-ink-900'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/search"
            aria-label="Search"
            className="rounded-lg p-2 text-ink-500 transition hover:bg-ink-50 hover:text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <SearchIcon />
          </Link>

          {isLoading ? (
            <div className="h-9 w-24 animate-pulse rounded-lg bg-ink-100" aria-hidden="true" />
          ) : user ? (
            <>
              <NotificationBell />
              <div className="group relative">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-lg p-1 pr-2 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  aria-haspopup="menu"
                >
                  <Avatar user={user} />
                  <span className="hidden max-w-[9rem] truncate text-sm font-medium text-ink-800 sm:block">
                    {user.display_name}
                  </span>
                </button>
                <div
                  role="menu"
                  className="invisible absolute right-0 top-full w-52 rounded-xl border border-ink-200 bg-white py-1.5 opacity-0 shadow-lg transition group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
                >
                  <MenuLink href="/profile">My profile</MenuLink>
                  <MenuLink href="/profile/contributions">My contributions</MenuLink>
                  <MenuLink href="/profile/bookmarks">Bookmarks</MenuLink>
                  <MenuLink href="/profile/verification">Professional verification</MenuLink>
                  {(user.role === 'GOVERNMENT_OFFICIAL' || user.role === 'ADMIN') && (
                    <MenuLink href="/government">Department dashboard</MenuLink>
                  )}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => void signOut()}
                    className="mt-1 w-full border-t border-ink-100 px-4 py-2.5 text-left text-sm text-ink-600 transition hover:bg-ink-50"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </>
          ) : (
            <button
              type="button"
              onClick={openLogin}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              Login
            </button>
          )}

          <Link
            href="/report"
            className="hidden rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 sm:inline-flex"
          >
            Raise a Problem
          </Link>

          <button
            type="button"
            onClick={() => setIsMenuOpen((open) => !open)}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-menu"
            aria-label="Toggle navigation menu"
            className="rounded-lg p-2 text-ink-600 transition hover:bg-ink-50 focus:outline-none focus:ring-2 focus:ring-brand-500 lg:hidden"
          >
            {isMenuOpen ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {isMenuOpen && (
        <div id="mobile-menu" className="border-t border-ink-200 bg-white lg:hidden">
          <nav aria-label="Mobile" className="mx-auto max-w-content px-4 py-3 sm:px-6">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 transition hover:bg-ink-50"
              >
                {link.label}
              </Link>
            ))}
            <div className="my-2 border-t border-ink-100" />
            {DISCOVERY_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block rounded-lg px-3 py-2.5 text-sm text-ink-500 transition hover:bg-ink-50"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/report"
              className="mt-3 block rounded-lg bg-brand-600 px-4 py-2.5 text-center text-sm font-semibold text-white"
            >
              Raise a Problem
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

function MenuLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      role="menuitem"
      className="block px-4 py-2.5 text-sm text-ink-700 transition hover:bg-ink-50"
    >
      {children}
    </Link>
  );
}

function Avatar({ user }: { user: { display_name: string; avatar_url: string } }) {
  if (user.avatar_url) {
    return (
      // A 32px avatar from Google is already small and already cached at the
      // edge; routing it through the image optimizer adds a hop and buys
      // nothing.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={user.avatar_url}
        alt=""
        width={32}
        height={32}
        className="h-8 w-8 rounded-full object-cover"
      />
    );
  }
  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800">
      {user.display_name.charAt(0).toUpperCase()}
    </span>
  );
}

function SearchIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="5.5" stroke="currentColor" strokeWidth="1.7" />
      <path d="m13.5 13.5 3 3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path d="M4 7h14M4 11h14M4 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path d="m6 6 10 10M16 6 6 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
