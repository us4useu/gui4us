import { defineConfig } from "vite";

// The dev server proxies the API to a running `gui4us --view web`, so `npm run dev` gives
// hot reload against real hardware.
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://127.0.0.1:7777",
      "/ws": { target: "ws://127.0.0.1:7777", ws: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
