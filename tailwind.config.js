/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: '#0A0A0F',
        panel: '#121218',
        linea: '#232329',
        magenta: '#FF2F6E',
        cyan: '#23E6C9',
        amber: '#FFB347',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Chakra Petch', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
