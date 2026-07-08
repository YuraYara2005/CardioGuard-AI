/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cg-bg':       '#09090f',
        'cg-surface':  '#12121e',
        'cg-card':     '#1a1a2e',
        'cg-border':   '#2a2a45',
        'cg-primary':  '#6366f1',
        'cg-accent':   '#06b6d4',
        'cg-danger':   '#ef4444',
        'cg-warning':  '#f59e0b',
        'cg-success':  '#10b981',
        'cg-text':     '#e2e8f0',
        'cg-muted':    '#64748b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'emergency-pulse': 'emergency-pulse 1s ease-in-out infinite',
        'fade-in-up':      'fade-in-up 0.4s ease-out both',
        'spin-slow':       'spin 3s linear infinite',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}