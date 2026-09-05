import type { Metadata, Viewport } from 'next';
import Script from 'next/script';

import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { AuthRequiredModal } from '@/features/authentication/AuthRequiredModal';
import { AuthProvider } from '@/features/authentication/auth-context';
import { CommunityBanner, CommunityPopup } from '@/features/community/WhatsAppInvite';

import './globals.css';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'JanDrishti — See. Suggest. Solve.',
    template: '%s | JanDrishti',
  },
  description:
    'A stronger tomorrow, together. A public-first civic platform bringing together public problems, evidence, professional experience and transparent government progress.',
  openGraph: {
    type: 'website',
    siteName: 'JanDrishti',
    title: 'JanDrishti — See. Suggest. Solve.',
    description:
      'Public problems, real evidence, professional recommendations and transparent progress, in one place.',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
  twitter: { card: 'summary_large_image', images: ['/og-image.png'] },
  robots: { index: true, follow: true },
  icons: { apple: '/apple-icon.png' },
};

export const viewport: Viewport = {
  // Address-bar and installed-app colour, taken from the wordmark navy.
  themeColor: '#112e46',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-ink-50 font-sans text-ink-800 antialiased">
        {/* Keyboard users should not have to tab through the whole navbar on
            every page (spec 59). */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow"
        >
          Skip to content
        </a>
        <AuthProvider>
          <CommunityBanner />
          <Navbar />
          <main id="main" className="flex-1">
            {children}
          </main>
          <Footer />
          <AuthRequiredModal />
          <CommunityPopup />
        </AuthProvider>
        <Script src="https://accounts.google.com/gsi/client" strategy="lazyOnload" />
      </body>
    </html>
  );
}
