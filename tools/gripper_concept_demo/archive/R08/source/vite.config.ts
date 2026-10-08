import { defineConfig } from "vite";
export default defineConfig({
  base: "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    watch: { ignored: ["**/archive/**", "**/NOTION_ARCHIVE.md"] },
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      input: {
        main: "index.html",
        engineering: "engineering.html",
        integrated: "integrated.html",
        concept: "concept.html",
      },
    },
  },
});
