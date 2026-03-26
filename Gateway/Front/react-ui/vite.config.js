import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        wechat: resolve(__dirname, "wechat/index.html"),
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 8501,
  },
  preview: {
    host: "0.0.0.0",
    port: 8501,
  },
});
