/** @type {import('tailwindcss').Config} */
import tailwindcssAnimate from 'tailwindcss-animate';

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: '#0b0d10',
        surface: '#15181d',
        border: '#2a3038',
        accent: '#4f8cff',
        profit: '#2fbf71',
        loss: '#e25555',
        warning: '#d99a2b',
        primary: '#e7e9ee',
        secondary: '#8b949e',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        control: '6px',
      },
      keyframes: {
        'fade-in': { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        'slide-in-bottom': { '0%': { transform: 'translateY(16px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        'slide-in-top': { '0%': { transform: 'translateY(-8px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } }
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out forwards',
        'slide-in-bottom': 'slide-in-bottom 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in-top': 'slide-in-top 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      }
    },
  },
  plugins: [
    tailwindcssAnimate,
  ],
};