import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production, netlify.toml proxies /data/* to GitHub Pages (live JSON, no redeploy).
// In dev, the seed files in public/data/ serve the same paths so the app runs standalone.
export default defineConfig({ plugins: [react()] });
