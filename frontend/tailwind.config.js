/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#121415',
        background: '#121415',
        surface: '#1E2021',
        surfaceAlt: '#282A2B',
        surfaceContainerLowest: '#0C0E0F',
        surfaceContainerLow: '#1A1C1D',
        surfaceContainer: '#1E2021',
        surfaceContainerHigh: '#282A2B',
        surfaceContainerHighest: '#333536',
        surfaceBright: '#38393A',
        line: 'rgba(156,142,129,0.22)',
        accent: '#F0BD7F',
        accentSoft: 'rgba(240,189,127,0.12)',
        primary: '#FFD3A0',
        primaryFixedDim: '#F0BD7F',
        tertiary: '#BDDEFF',
        violet: '#BDDEFF',
        textMain: '#E2E2E3',
        textMuted: '#D3C4B5',
        onBackground: '#E2E2E3',
        onSurface: '#E2E2E3',
        onSurfaceVariant: '#D3C4B5',
        onPrimary: '#462A00',
        onErrorContainer: '#FFDAD6',
        success: '#BDDEFF',
        warning: '#F0BD7F',
        danger: '#FFB4AB',
        error: '#FFB4AB',
        errorContainer: '#93000A',
        outlineVariant: '#4F453A',
        ink: '#0C0E0F',
      },
      fontFamily: {
        headline: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        label: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(240,189,127,0.18), 0 28px 80px rgba(0,0,0,0.48)',
        panel: '0 24px 80px rgba(0,0,0,0.36)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
      backgroundImage: {
        'observer-grid':
          'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
};
