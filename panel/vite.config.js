import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/panel/",
  server: {
    port: 5174,
    // Lokal ishlab chiqishda API Django'ga yo'naltiriladi (sessiya cookie'lari bir domenda qoladi)
    proxy: { "/api": "http://localhost:8000" },
  },
});
