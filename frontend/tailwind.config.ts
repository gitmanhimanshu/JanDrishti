import type { Config } from 'tailwindcss';

/**
 * The palette is sampled from the JanDrishti mark, not invented alongside it.
 *
 * The logo is a tricolour eye: a saffron and green swoosh forming the lid, a
 * navy figure at the centre of three raised-arm figures, and an iris holding
 * India, a sunrise, a road and a leaf. Three colours therefore carry meaning
 * here, and they are used for what they mean rather than decoratively:
 *
 *   brand (navy/blue)  primary identity, actions, links      #112e46 → #0562ad
 *   saffron            energy, urgency, the call to act      #ed6a08
 *   leaf (green)       resolution, growth, proof of work     #044e26 → #247032
 *
 * `brand` keeps its name so every existing component adopts the new identity
 * without a rename sweep.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Sampled: "Jan" wordmark #112e46, centre figure #034f93, "See" #0562ad.
        brand: {
          50: '#f1f6fb',
          100: '#dfeaf5',
          200: '#bcd3e9',
          300: '#8db3d6',
          400: '#5089bd',
          500: '#0562ad',
          600: '#034f93',
          700: '#02437d',
          800: '#0b3457',
          900: '#112e46',
          950: '#0a1d2e',
        },
        // Sampled: swoosh #f48e12, "Suggest" #ed6a08, left figure #e46f04.
        saffron: {
          50: '#fff8ed',
          100: '#ffeed4',
          200: '#fdd9a8',
          300: '#fbbd71',
          400: '#f8a03c',
          500: '#f48e12',
          600: '#ed6a08',
          700: '#c25105',
          800: '#9a410b',
          900: '#7c360d',
        },
        // Sampled: eye lower #044e26, right figure #247032, swoosh #2e762e.
        leaf: {
          50: '#f0f8f1',
          100: '#dbefdd',
          200: '#b7dfbb',
          300: '#87c78d',
          400: '#52a75c',
          500: '#2e762e',
          600: '#247032',
          700: '#1a5928',
          800: '#044e26',
          900: '#053a1d',
        },
        // Neutral text and surfaces. Slightly warm, to sit with the off-white
        // #f7f7f7 the logo is drawn on.
        ink: {
          50: '#f7f7f7',
          100: '#ededee',
          200: '#d9dadc',
          300: '#b7b9bd',
          400: '#8d9096',
          500: '#6c6f76',
          600: '#55585e',
          700: '#45474c',
          800: '#37393d',
          900: '#1f2124',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      maxWidth: { content: '76rem' },
      backgroundImage: {
        // The sunrise inside the iris, reused as a section wash.
        sunrise: 'linear-gradient(180deg, #fff8ed 0%, #f7f7f7 60%)',
        // The saffron-over-green swoosh that forms the eyelid.
        tricolour: 'linear-gradient(90deg, #ed6a08 0%, #f48e12 35%, #2e762e 65%, #044e26 100%)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'iris-in': {
          '0%': { opacity: '0', transform: 'scale(0.94)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        // Subtle, and only where it helps the eye find the order of things.
        'fade-up': 'fade-up 0.5s ease-out both',
        'iris-in': 'iris-in 0.7s ease-out both',
      },
    },
  },
  plugins: [],
};

export default config;
