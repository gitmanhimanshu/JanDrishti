import type { Metadata } from 'next';

import { PrimaryLink, SecondaryLink } from '@/components/ui/States';

export const metadata: Metadata = {
  title: 'How It Works',
  description:
    'How a problem moves from a citizen report through evidence, professional recommendations and government action to published proof.',
  alternates: { canonical: '/how-it-works' },
};

const LIFECYCLE = [
  {
    status: 'Submitted',
    detail: 'A citizen reports the problem with a location and whatever evidence they have.',
  },
  {
    status: 'Under review / Verified',
    detail: 'A moderator checks the report is genuine and correctly described.',
  },
  {
    status: 'Department assigned',
    detail:
      'Routing by category and jurisdiction sends it to the responsible department. Where routing is uncertain, a person assigns it.',
  },
  { status: 'Acknowledged', detail: 'The department confirms it has the issue.' },
  { status: 'Inspection', detail: 'Officials visit and record what they find.' },
  { status: 'Action planned', detail: 'A plan and an expected timeline are published.' },
  { status: 'Work started / in progress', detail: 'Work begins, with progress updates.' },
  { status: 'Completed', detail: 'The department reports the work done, with after evidence.' },
  {
    status: 'Verification',
    detail:
      'The claim is checked against the evidence. If it does not hold up, the issue goes back to the department rather than quietly closing.',
  },
  { status: 'Resolved', detail: 'The issue is closed, and the whole record stays public.' },
];

const FAQS = [
  {
    question: 'Do I need an account to read anything?',
    answer:
      'No. Every problem, experience, project and progress update is public. An account is only needed to take part — to support an issue, comment, upload evidence or submit something of your own.',
  },
  {
    question: 'What does the verified badge mean?',
    answer:
      'It means JanDrishti has reviewed a document supporting that professional claim. It is not an endorsement of anything the person says, and it does not make their recommendations correct.',
  },
  {
    question: 'What if five hundred people report the same pothole?',
    answer:
      'Similar reports about the same location are grouped so the department sees one work item, while the public sees how many people are affected. Every original report is preserved in full, with its own author and evidence — nothing is deleted.',
  },
  {
    question: 'Is uploaded evidence trustworthy?',
    answer:
      'Uploaded evidence is labelled as uploaded, not verified. Only evidence a person has actually checked carries a verified mark. The interface never blurs that distinction.',
  },
  {
    question: 'Can I report something without my name on it?',
    answer:
      'Yes. Your name is hidden from the public page. Your account is still recorded internally so moderation and audit remain possible, so this is anonymity from other users rather than from the platform.',
  },
  {
    question: 'Does an AI decide whether my complaint is true?',
    answer:
      'No. Automated tools help with categorising, routing and spotting probable duplicates. Whether an allegation is true, whether evidence is genuine, and whether a professional claim is verified are all human decisions.',
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-ink-900">How JanDrishti works</h1>
      <p className="mt-3 text-base leading-relaxed text-ink-600">
        A complaint disappears into an inbox. A documented problem — with a location, evidence,
        professional judgement and a public record of what was done about it — is much harder to
        ignore.
      </p>

      <section aria-labelledby="lifecycle-heading" className="mt-12">
        <h2 id="lifecycle-heading" className="text-xl font-semibold text-ink-900">
          The life of a problem
        </h2>
        <p className="mt-1.5 text-sm text-ink-500">
          A problem moves through defined stages. It cannot skip them, and each change is recorded
          publicly with who made it and when.
        </p>
        <ol className="mt-6">
          {LIFECYCLE.map((stage, index) => (
            <li key={stage.status} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-[11px] font-semibold text-white">
                  {index + 1}
                </span>
                {index < LIFECYCLE.length - 1 && (
                  <span aria-hidden="true" className="my-1 w-px flex-1 bg-ink-200" />
                )}
              </div>
              <div className="pb-6">
                <p className="text-sm font-semibold text-ink-900">{stage.status}</p>
                <p className="mt-0.5 text-sm leading-relaxed text-ink-600">{stage.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="faq-heading" className="mt-12">
        <h2 id="faq-heading" className="text-xl font-semibold text-ink-900">
          Common questions
        </h2>
        <dl className="mt-6 space-y-6">
          {FAQS.map((faq) => (
            <div key={faq.question}>
              <dt className="text-sm font-semibold text-ink-900">{faq.question}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed text-ink-600">{faq.answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="mt-12 flex flex-col gap-3 border-t border-ink-200 pt-8 sm:flex-row">
        <PrimaryLink href="/report">Report a Problem</PrimaryLink>
        <SecondaryLink href="/problems">Explore Problems</SecondaryLink>
      </div>
    </div>
  );
}
