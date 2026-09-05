/**
 * Landing page.
 *
 * Composed of one section per idea, in the order the story needs:
 *
 *   hero        raise it, and watch it move — over the civic backdrop
 *   experience  why this is not a complaint portal (placed early on purpose)
 *   discussion  deciding what should be done, not only getting it fixed
 *   problems    what the community is actually facing
 *   collective  how one report becomes a signal
 *   evidence    what you can attach, and what "verified" really means
 *   action      progress you can check
 *   projects    problems that became funded work
 *   howItWorks  the six steps, named
 *   trust       people, experience, evidence, action
 *   finalCta    back to the person raising something
 *
 * A server component: public content is server-rendered so it is fast,
 * indexable and readable without JavaScript. Live figures come from the API —
 * a deployment with no activity says so instead of inventing totals.
 */
import type { Metadata } from 'next';

import { CollectiveVoice } from '@/features/landing/CollectiveVoice';
import { DiscussionSection } from '@/features/landing/DiscussionSection';
import { EvidenceSection } from '@/features/landing/EvidenceSection';
import { ExperienceSection } from '@/features/landing/ExperienceSection';
import { FinalCta } from '@/features/landing/FinalCta';
import { HeroSection } from '@/features/landing/HeroSection';
import { JourneySection } from '@/features/landing/JourneySection';
import { Pillars } from '@/features/landing/Pillars';
import { ProblemExplorer } from '@/features/landing/ProblemExplorer';
import { ProjectsSection } from '@/features/landing/ProjectsSection';
import { TransparentAction } from '@/features/landing/TransparentAction';
import { fetchPublic, fetchPublicPage } from '@/services/api-client';
import type { ProblemCard, PublicStats } from '@/types/api';

export const metadata: Metadata = {
  title: 'JanDrishti — Raise What Matters. See It Move.',
  description:
    'Report real problems, share experience and ideas, bring people together, and see meaningful action happen. A public-first civic intelligence and action platform.',
  alternates: { canonical: '/' },
  openGraph: {
    title: 'JanDrishti — Raise What Matters. See It Move.',
    description:
      'Problems, people, experience, ideas, action and proof — in one public place.',
    images: ['/og-image.png'],
  },
};

export const revalidate = 60;

const EMPTY_STATS: PublicStats = {
  problems_reported: 0,
  active_problems: 0,
  problems_resolved: 0,
  citizens_supporting: 0,
  experiences_shared: 0,
  government_responses: 0,
  projects_completed: 0,
  average_resolution_days: null,
  computed_at: '',
};

export default async function HomePage() {
  const [stats, trending] = await Promise.all([
    fetchPublic<PublicStats>('/stats/public/', EMPTY_STATS),
    fetchPublicPage<ProblemCard>('/problems/?tab=trending&page_size=6'),
  ]);

  return (
    <>
      <HeroSection stats={stats} />
      <ExperienceSection />
      <DiscussionSection />
      <ProblemExplorer problems={trending.results} />
      <CollectiveVoice />
      <EvidenceSection />
      <TransparentAction />
      <ProjectsSection />
      <JourneySection />
      <Pillars />
      <FinalCta />
    </>
  );
}
