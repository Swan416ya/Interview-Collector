import axios from "axios";

/**
 * 生产或直连：设置 VITE_API_BASE_URL（末尾不要斜杠）。
 * 本地 `npm run dev`：未设置时走空基址 + Vite 代理 `/api`，与页面同源，避免 fetch 流式接口因 CORS 报 Failed to fetch。
 */
export function resolveApiBaseURL(): string {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (typeof v === "string" && v.trim() !== "") {
    return v.trim().replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "";
  }
  return "http://localhost:8000";
}

export const apiClient = axios.create({
  baseURL: resolveApiBaseURL(),
  timeout: 30000
});

