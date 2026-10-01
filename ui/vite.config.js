import { defineConfig } from "vite";
import { resolve } from "path";

// The build goes straight into the Python package (gui4us/view/web/static), next to the widget
// bundles, so that `pip install gui4us` ships a working browser view -- no Node needed by users.
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
    // Chromium 83: the Qt 5.15 WebEngine of the gui4us application window (gui4us.view.web.window).
    target: ["es2020", "chrome83"],
    outDir: resolve(__dirname, "../gui4us/view/web/static"),
    emptyOutDir: true,
  },
});
