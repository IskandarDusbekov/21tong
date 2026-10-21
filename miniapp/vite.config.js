import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Lokal ishlab chiqishda /api so'rovlari Django'ga yo'naltiriladi
    proxy: { "/api": "http://localhost:8000" },
  },
});
