/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#172026",
        panel: "#ffffff",
        line: "#dbe3ea",
        ocean: "#2563eb",
        mint: "#0f766e",
        amber: "#b45309",
      },
    },
  },
  plugins: [],
};

