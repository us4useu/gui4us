import { defineConfig } from "vite";
import { resolve } from "path";

// Builds one self-contained ES module per Jupyter widget. anywidget evaluates `_esm` as a
// single module, so the widget entries must not contain unresolved relative imports.
// Output goes straight into the Python package, from where widgets.py loads it.
export default defineConfig({
  build: {
    outDir: resolve(__dirname, "../gui4us/view/jupyter/static"),
    emptyOutDir: true,
    lib: {
      entry: {
        display: resolve(__dirname, "src/widgets/display.js"),
        controls: resolve(__dirname, "src/widgets/controls.js"),
        actions: resolve(__dirname, "src/widgets/actions.js"),
        capture: resolve(__dirname, "src/widgets/capture.js"),
      },
      formats: ["es"],
    },
    rollupOptions: {
      output: { entryFileNames: "[name].js" },
    },
  },
});
