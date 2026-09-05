/**
 * Original figure and glyph illustrations for the landing story.
 *
 * The raised-hands citizen is the emotional anchor of the brand: arms up in an
 * open V, chin level, weight even. That reads as *raising something*, not
 * surrendering — surrender is palms-forward with the head down, so the arms
 * here angle outward and the head stays upright.
 *
 * Deliberately geometric and flat rather than cartoonish: simple volumes, no
 * faces, no outlines. Faceless figures also let any viewer see themselves in
 * them, which matters more here than character.
 */

export type FigureTone = 'navy' | 'saffron' | 'leaf' | 'sky' | 'slate';

const TONES: Record<FigureTone, { body: string; head: string; limb: string }> = {
  navy: { body: '#034f93', head: '#112e46', limb: '#02437d' },
  saffron: { body: '#ed6a08', head: '#9a410b', limb: '#c25105' },
  leaf: { body: '#247032', head: '#044e26', limb: '#1a5928' },
  sky: { body: '#5089bd', head: '#0b3457', limb: '#34719f' },
  slate: { body: '#6c6f76', head: '#37393d', limb: '#55585e' },
};

/**
 * The signature gesture. One citizen raising what matters.
 */
export function RaisedHandsFigure({
  tone = 'navy',
  className = '',
  title,
}: {
  tone?: FigureTone;
  className?: string;
  title?: string;
}) {
  const c = TONES[tone];
  return (
    <svg
      viewBox="0 0 120 172"
      fill="none"
      className={className}
      role={title ? 'img' : 'presentation'}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {/* Limbs are round-capped strokes rather than filled blobs: it keeps the
          silhouette slim and reads as drawn rather than clip-art. */}
      <path
        d="M47 66 L30 36"
        stroke={c.limb}
        strokeWidth="9"
        strokeLinecap="round"
      />
      <path
        d="M73 66 L90 36"
        stroke={c.limb}
        strokeWidth="9"
        strokeLinecap="round"
      />
      <circle cx="28" cy="32" r="6" fill={c.limb} />
      <circle cx="92" cy="32" r="6" fill={c.limb} />

      <circle cx="60" cy="42" r="12.5" fill={c.head} />

      {/* Torso: shoulders wider than the waist, so the stance reads as open. */}
      <path
        d="M60 58c12 0 19 8 19 19l-2 27c0 6-5 9-17 9s-17-3-17-9l-2-27c0-11 7-19 19-19Z"
        fill={c.body}
      />

      <path d="M53 112 L51 158" stroke={c.head} strokeWidth="11" strokeLinecap="round" />
      <path d="M67 112 L69 158" stroke={c.head} strokeWidth="11" strokeLinecap="round" />
    </svg>
  );
}

/** A citizen standing with others — used for the crowd that joins in. */
export function StandingFigure({
  tone = 'slate',
  className = '',
}: {
  tone?: FigureTone;
  className?: string;
}) {
  const c = TONES[tone];
  return (
    <svg viewBox="0 0 80 152" fill="none" className={className} aria-hidden="true">
      <circle cx="40" cy="24" r="12" fill={c.head} />
      {/* Arms held at the sides — present and steady, not raising. */}
      <path d="M27 50 L23 88" stroke={c.limb} strokeWidth="8" strokeLinecap="round" />
      <path d="M53 50 L57 88" stroke={c.limb} strokeWidth="8" strokeLinecap="round" />
      <path
        d="M40 39c11 0 18 8 18 18l-2 26c0 6-5 9-16 9s-16-3-16-9l-2-26c0-10 7-18 18-18Z"
        fill={c.body}
      />
      <path d="M34 94 L32 140" stroke={c.head} strokeWidth="10" strokeLinecap="round" />
      <path d="M46 94 L48 140" stroke={c.head} strokeWidth="10" strokeLinecap="round" />
    </svg>
  );
}

/** Compact avatar for support counts and converging-citizen rows. */
export function AvatarDot({
  tone = 'navy',
  className = '',
  style,
}: {
  tone?: FigureTone;
  className?: string;
  /** Used by the hero to stagger the crowd arriving. */
  style?: React.CSSProperties;
}) {
  const c = TONES[tone];
  return (
    <svg viewBox="0 0 40 40" className={className} style={style} aria-hidden="true">
      <circle cx="20" cy="20" r="20" fill={c.body} opacity="0.16" />
      <circle cx="20" cy="15.5" r="6" fill={c.head} />
      <path d="M20 23c6 0 10 4 10 9v2H10v-2c0-5 4-9 10-9Z" fill={c.head} />
    </svg>
  );
}

/* --------------------------------------------------------------- glyphs */

/**
 * Civic problem glyphs.
 *
 * Drawn as neutral objects rather than distress imagery — the page moves from
 * problem to action, so the problems are stated plainly, not dramatised.
 */

export function PotholeGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <path d="M4 34h40" stroke="#b7b9bd" strokeWidth="3" strokeLinecap="round" />
      <path
        d="M14 34c0-5 4-8 9-8s10 3 10 8c0 3-4 5-9.5 5S14 37 14 34Z"
        fill="#37393d"
        opacity="0.85"
      />
      <path d="M10 42h28" stroke="#d9dadc" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function GarbageGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <rect x="13" y="18" width="22" height="24" rx="3" fill="#6c6f76" />
      <path d="M10 16h28" stroke="#37393d" strokeWidth="3" strokeLinecap="round" />
      <circle cx="19" cy="10" r="4" fill="#8d9096" />
      <circle cx="28" cy="8" r="5" fill="#b7b9bd" />
      <circle cx="34" cy="13" r="3.5" fill="#8d9096" />
    </svg>
  );
}

export function StreetlightGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <path d="M18 44V14a8 8 0 0 1 8-8h6" stroke="#6c6f76" strokeWidth="3.5" strokeLinecap="round" />
      <rect x="28" y="4" width="14" height="8" rx="3" fill="#8d9096" />
      {/* Dark lamp: the light is out, which is the point. */}
      <path d="M31 12h8l-4 6-4-6Z" fill="#37393d" />
    </svg>
  );
}

export function WaterGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <path d="M6 30h36" stroke="#b7b9bd" strokeWidth="3" strokeLinecap="round" />
      <path
        d="M24 8c5 7 9 11 9 16a9 9 0 0 1-18 0c0-5 4-9 9-16Z"
        fill="#5089bd"
        opacity="0.9"
      />
      <path d="M9 38h30" stroke="#5089bd" strokeWidth="3" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

export function CheckGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M5 12.5 10 17.5 19 7"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * The connecting thread between story stages.
 *
 * Hidden on small screens, where the story stacks vertically and the thread
 * would point the wrong way.
 */
export function FlowConnector({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 120 24"
      fill="none"
      preserveAspectRatio="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M2 12h100"
        stroke="#b7b9bd"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="6 7"
      />
      <path
        d="M100 6l10 6-10 6"
        stroke="#b7b9bd"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
