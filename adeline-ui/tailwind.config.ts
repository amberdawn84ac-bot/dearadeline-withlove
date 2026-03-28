import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Adeline lesson block palette ──
        'paper-light': '#FFFEF7',
        'paper-medium': '#FAF5E4',
        'golden-wheat': '#BD6809',
        'ink-brown': '#121B13',
        'deep-purple': '#9A3F4A',
        'forest-green': '#2F4731',
        'fuschia-dark': '#3D1419',
        'border-brown': '#E7DAC3',
        'highlight-yellow': '#FFF9C4',
        'highlight-pink': '#FCE4EC',
        'highlight-mint': '#E8F5E9',
        'neon-fuschia': '#9A3F4A',
        'neon-orange': '#BD6809',
        
        // Sketchnote Design System — Dear Adeline 2.0
        papaya: {
          DEFAULT: "#BD6809",
          light: "#D4820F",
          dark: "#9A5507",
        },
        paradise: {
          DEFAULT: "#9A3F4A",
          light: "#B04A57",
          dark: "#7D333D",
        },
        fuschia: {
          DEFAULT: "#3D1419",
          light: "#52202A",
          dark: "#2A0D12",
        },
        // Neutral parchment tones for the Sketchnote feel
        parchment: {
          50: "#FDF8F0",
          100: "#F9EDD8",
          200: "#F0D9B0",
          300: "#E3C07A",
        },

        // ── Muted jewel tone companions ──────────────────────────
        // Dusty, field-pressed — nothing bright or synthetic.
        sage: {
          DEFAULT: "#6B7F5E",
          light: "#8A9E7B",
          dark: "#526148",
        },
        slate: {
          DEFAULT: "#4A5E72",
          light: "#617A90",
          dark: "#364858",
        },
        plum: {
          DEFAULT: "#6B4E6B",
          light: "#856485",
          dark: "#533C53",
        },
        ochre: {
          DEFAULT: "#8C6D3F",
          light: "#A8865A",
          dark: "#6E5430",
        },
        ink: {
          DEFAULT: "#2C2318",
          light: "#3D3020",
          dark: "#1A1510",
        },
      },
      fontFamily: {
        sketch: ["'Patrick Hand'", "cursive"],
        body: ["'Lora'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        // Adeline's handwritten fonts
        'emilys-candy': ['var(--font-emilys-candy)', 'cursive'],
        'kalam': ['var(--font-kalam)', 'cursive'],
        'kranky': ['var(--font-kranky)', 'cursive'],
        'permanent-marker': ['var(--font-permanent-marker)', 'cursive'],
        'swanky': ['var(--font-swanky)', 'cursive'],
      },
      backgroundImage: {
        "sketch-paper": "url('/textures/paper.png')",
      },
      keyframes: {
        'fade-slide-in': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-slide-in': 'fade-slide-in 0.5s ease-out',
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
