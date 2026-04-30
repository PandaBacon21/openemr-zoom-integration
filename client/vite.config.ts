import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:5000",
      "/health": "http://localhost:5000",
      "/config": "http://localhost:5000",
      "/zoom": "http://localhost:5000",
      "/openemr": "http://localhost:5000",
      "/webhooks": "http://localhost:5000",
      "/audit": "http://localhost:5000",
      "/rest": "http://localhost:5000",
    },
  },
  build: {
    outDir: "../server/app/static",
    emptyOutDir: true,
  },
});
