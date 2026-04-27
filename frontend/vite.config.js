import fs from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const httpsCertFile = process.env.HTTPS_CERT_FILE;
const httpsKeyFile = process.env.HTTPS_KEY_FILE;
const useHttps = Boolean(httpsCertFile && httpsKeyFile && fs.existsSync(httpsCertFile) && fs.existsSync(httpsKeyFile));

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    https: useHttps
      ? {
          cert: fs.readFileSync(httpsCertFile),
          key: fs.readFileSync(httpsKeyFile),
        }
      : false,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_TARGET || "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
