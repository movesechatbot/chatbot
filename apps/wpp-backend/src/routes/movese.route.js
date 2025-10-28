// routes/movese.route.js (ESM)
import express from "express";

const router = express.Router();
const FLASK = (process.env.FLASK_URL || "http://127.0.0.1:5000").replace(/\/+$/, "");

// Envia texto do cliente para o Flask e reemite user+bot via Socket.IO
router.post("/hook", async (req, res) => {
  const io = req.app.get("io");
  console.log("[HOOK] payload:", JSON.stringify(req.body));

  const { user_id, messages = [] } = req.body || {};

  console.log("[HOOK] recebido do Flask:", { user_id, count: messages.length });

  if (!user_id || !Array.isArray(messages)) {
    console.log("[HOOK] payload inválido:", req.body);
    return res.status(400).json({ ok: false, error: "bad_payload" });
  }

  for (const m of messages) {
    const msg = {
      id: `${user_id}-${Date.now()}-${m.sender === "me" ? "u" : "b"}`,
      sender: m.sender,
      text: m.text || "",
      timestamp: m.timestamp || Math.floor(Date.now() / 1000),
    };
    // EMITE em vários nomes de evento (defensivo)
    io.emit("message", { user_id, message: msg });
    io.emit("newMessage", { user_id, message: msg });
    io.emit("receiveMessage", { user_id, message: msg });
  }

  return res.json({ ok: true });
});


// (Opcional) Proxies de leitura — requer os endpoints no Flask:
// GET /api/v1/messages/<user_id>  e  GET /api/v1/conversations
router.get("/messages/:uid", async (req, res) => {
  try {
    const r = await fetch(`${FLASK}/api/v1/messages/${encodeURIComponent(req.params.uid)}`);
    return res.status(200).json(await r.json());
  } catch (e) {
    return res.status(500).json({ ok: false, error: "flask_unreachable" });
  }
});

router.get("/conversations", async (req, res) => {
  try {
    const r = await fetch(`${FLASK}/api/v1/conversations`);
    return res.status(200).json(await r.json());
  } catch (e) {
    return res.status(500).json({ ok: false, error: "flask_unreachable" });
  }
});

export default router;
