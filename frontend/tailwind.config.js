/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      animation: {
        "star-btn": "star-btn var(--duration, 3s) linear infinite",
      },
      keyframes: {
        "star-btn": {
          "0%": { "offset-distance": "0%" },
          "100%": { "offset-distance": "100%" },
        },
      },
    },
  },
  plugins: [],
}
