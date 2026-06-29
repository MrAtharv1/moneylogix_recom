/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: '#0f1117',
        surface: '#1a1d27',
        border: '#2d3148',
        accent: '#3b82f6',
        profit: '#22c55e',
        loss: '#ef4444',
        warning: '#f59e0b',
        primary: '#e2e8f0',
        secondary: '#94a3b8',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        card: '8px',
        control: '4px',
      },
    },
  },
  plugins: [],
}
