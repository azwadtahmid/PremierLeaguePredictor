// Builds the website into ../docs, which GitHub Pages serves.
// docs/data.json is written by src/site.py every morning and is NOT touched by
// the build: emptyOutDir is off and asset names are fixed, so a rebuild only
// replaces index.html and docs/assets/*.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const DATA = fileURLToPath(new URL("../docs/data.json", import.meta.url));

// During `npm run dev`, serve the real data file so the site shows live data.
const liveData = (): Plugin => ({
  name: "live-data",
  configureServer(server) {
    server.middlewares.use("/data.json", (_req, res) => {
      res.setHeader("Content-Type", "application/json");
      res.end(readFileSync(DATA));
    });
  },
});

export default defineConfig({
  base: "./",
  plugins: [react(), liveData()],
  publicDir: false,
  build: {
    outDir: "../docs",
    emptyOutDir: false,
    // React + Remotion Player is ~190 kB gzipped in one file; fine for this site.
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        entryFileNames: "assets/app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
