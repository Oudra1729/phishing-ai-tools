import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const target = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:5000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": target,
      "/predict": target,
      "/explain": target,
      "/examples": target,
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
