/**
 * Single source of truth for the backend API's base URL.
 *
 * Local dev (opening the frontend via a local server on 127.0.0.1/localhost)
 * talks to the local Django server. Everything else (Netlify) talks to the
 * deployed Render backend — update RENDER_API_URL once you know your real
 * Render service URL.
 */
const LOCAL_API_URL = "http://127.0.0.1:8000/api";
const RENDER_API_URL = "https://funkies254-api.onrender.com/api";

const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);

export const API_BASE_URL = isLocalHost ? LOCAL_API_URL : RENDER_API_URL;
