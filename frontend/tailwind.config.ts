import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#3f3028",
        line: "#cdbfb2",
        surface: "#f7f4ee",
        brand: "#99775c",
        accent: "#765a46",
        narvik: "#eae7dd",
        sorrell: "#99775c"
      },
    },
  },
  plugins: [],
} satisfies Config;
