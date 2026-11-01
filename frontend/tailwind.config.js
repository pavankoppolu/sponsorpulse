/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        stage: {
          discovered: '#3b82f6',
          enriched: '#a855f7',
          drafted: '#f59e0b',
          ready: '#10b981',
          sent: '#0ea5e9',
          replied: '#22c55e',
          closed: '#64748b'
        }
      }
    },
  },
  plugins: [],
}
