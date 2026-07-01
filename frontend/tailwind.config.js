/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#e2e8f0",
        "ink-muted": "#94a3b8",
        "ink-faint": "#64748b",
        navy: {
          950: "#020617",
          900: "#0f172a",
          800: "#1e293b",
          700: "#334155",
          600: "#475569",
        },
        panel: "rgba(15, 23, 42, 0.7)",
        "panel-solid": "#0f172a",
        line: "rgba(148, 163, 184, 0.15)",
        "line-strong": "rgba(148, 163, 184, 0.25)",
        ocean: "#6366f1",
        "ocean-light": "#818cf8",
        cyan: "#06b6d4",
        mint: "#14b8a6",
        amber: "#f59e0b",
        rose: "#f43f5e",
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4)",
        "gradient-card": "linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(6, 182, 212, 0.05))",
        "gradient-glow": "radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(99, 102, 241, 0.06), transparent 40%)",
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
