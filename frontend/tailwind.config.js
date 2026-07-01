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
        "ink-muted": "#526173",
        "ink-faint": "#7a8797",
        navy: {
          950: "#f6f8fb",
          900: "#eef2f7",
          800: "#e2e8f0",
          700: "#cbd5e1",
          600: "#94a3b8",
        },
        panel: "rgba(255, 255, 255, 0.88)",
        "panel-solid": "#ffffff",
        line: "rgba(82, 97, 115, 0.16)",
        "line-strong": "rgba(82, 97, 115, 0.28)",
        ocean: "#2563eb",
        "ocean-light": "#1d4ed8",
        cyan: "#0891b2",
        mint: "#0f766e",
        amber: "#b45309",
        rose: "#be123c",
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #2563eb, #0891b2)",
        "gradient-card": "linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(8, 145, 178, 0.04))",
        "gradient-glow": "linear-gradient(180deg, rgba(37, 99, 235, 0.05), transparent)",
      },
      animation: {
        "float-slow": "float 20s ease-in-out infinite",
        "float-medium": "float 14s ease-in-out infinite reverse",
        "float-fast": "float 10s ease-in-out infinite",
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "slide-up": "slideUp 0.5s ease-out forwards",
        "glow-pulse": "glowPulse 3s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "25%": { transform: "translate(30px, -40px) scale(1.05)" },
          "50%": { transform: "translate(-20px, 20px) scale(0.95)" },
          "75%": { transform: "translate(15px, -10px) scale(1.02)" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(24px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        glowPulse: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.8" },
        },
        shimmer: {
          from: { backgroundPosition: "-200% 0" },
          to: { backgroundPosition: "200% 0" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
