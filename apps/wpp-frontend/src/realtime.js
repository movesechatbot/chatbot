// src/realtime.js
import { io } from "socket.io-client";

const isLocal = ["localhost", "127.0.0.1"].includes(location.hostname);
export const API_BASE = isLocal
  ? "http://localhost:10000"
  : "https://chatbot-pfee.onrender.com";

let socket;

export function initRealtime(uid, { onAssistantMessage, onTyping } = {}) {
  socket = io(API_BASE, { transports: ["websocket"] });

  socket.on("connect", () => {
    socket.emit("join", { uid });
  });

  socket.on("typing", (data) => {
    if (data?.uid !== uid || data?.role !== "assistant") return;
    onTyping?.(!!data.is_typing);
  });

  socket.on("message_out", (msg) => {
    if (msg?.uid !== uid) return;
    onAssistantMessage?.(msg);
  });

  socket.on("error", (e) => console.warn("socket error", e));
}

export async function sendUserMessage(uid, text) {
  // indica que o user está digitando (opcional)
  socket?.emit?.("typing", { uid, role: "user", is_typing: true });

  const ENDPOINT = `${API_BASE}/chat`;
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uid, text }),
  }).finally(() => {
    socket?.emit?.("typing", { uid, role: "user", is_typing: false });
  });

  // você pode confiar só no message_out; o retorno aqui é opcional
  return res.ok ? res.json() : {};
}
