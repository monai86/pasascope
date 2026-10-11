import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  // The product is light-only. With the class strategy and no `.dark` class
  // ever applied, a stray `dark:` variant cannot follow the OS setting.
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "var(--color-text-strong)",
          muted: "var(--color-text-muted)",
          subtle: "var(--color-text-subtle)",
        },
        line: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
        },
        field: "var(--color-surface-strong)",
        canvas: "var(--color-page-bg)",
        surface: {
          DEFAULT: "var(--color-surface-strong)",
          soft: "var(--color-surface)",
          muted: "var(--color-surface-muted)",
          control: "var(--color-surface-control)",
        },
        brand: {
          DEFAULT: "var(--color-brand)",
          hover: "var(--color-brand-hover)",
          strong: "var(--color-brand-strong)",
          soft: "var(--color-brand-soft)",
          border: "var(--color-brand-border)",
        },
        highlight: {
          DEFAULT: "var(--color-highlight)",
          soft: "var(--color-highlight-soft)",
          border: "var(--color-highlight-border)",
          text: "var(--color-highlight-text)",
        },
        tint: {
          DEFAULT: "var(--color-sky)",
          soft: "var(--color-sky-soft)",
          strong: "var(--color-sky-strong)",
        },
        navy: "var(--color-navy)",
      },
      fontFamily: {
        sans: ["var(--font-product)"],
        display: ["var(--font-display)"],
      },
      fontSize: {
        // The UI audit rejects visible text under 12px, so the smallest step is 12px.
        "2xs": ["0.75rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        "2xs": "0 1px 1px rgba(22, 35, 63, 0.04)",
        xs: "0 1px 2px rgba(22, 35, 63, 0.05)",
        soft: "var(--shadow-soft)",
        lift: "var(--shadow-lift)",
        floating: "var(--shadow-floating)",
      },
      backdropBlur: {
        xs: "2px",
        glass: "var(--glass-blur)",
      },
      borderRadius: {
        control: "var(--radius-control)",
        card: "var(--radius-card)",
        panel: "var(--radius-panel)",
        shell: "var(--radius-shell)",
      },
      borderWidth: {
        3: "3px",
      },
      ringWidth: {
        3: "3px",
      },
      scale: {
        98: "0.98",
      },
      gridTemplateColumns: {
        24: "repeat(24, minmax(0, 1fr))",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in var(--motion-panel) var(--motion-ease) both",
      },
    },
  },
  plugins: [],
};

export default config;
