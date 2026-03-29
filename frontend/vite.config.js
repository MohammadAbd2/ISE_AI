import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Keep the frontend on a predictable local port that matches the README.
    port: 5173,
  },
});
