// ==================== STATE ====================
let contacts = [];            // lista lateral (vem de /admin/conversas)
let cacheMessages = {};       // { user_id: [msgs] }
let currentChatId = null;     // conversa aberta

// ==================== DOM ======================
const conversationList = document.querySelector(".conversation-list");
const messagesArea      = document.getElementById("messagesArea");
const messageInput      = document.getElementById("messageInput");
const sendBtn           = document.getElementById("sendBtn");
const chatName          = document.getElementById("chatName");
const chatStatus        = document.getElementById("chatStatus");
const chatAvatar        = document.getElementById("chatAvatar");
const themeToggle       = document.getElementById("themeToggle");
const backToList        = document.getElementById("backToList");
const scrollBottomBtn   = document.getElementById("scrollBottomBtn");
const contextMenu       = document.getElementById("contextMenu");
const sidebarColumn     = document.getElementById("sidebarColumn");
const chatColumn        = document.getElementById("chatColumn");

const DEFAULT_AVATAR = "/static/placeholder.svg"; // ajuste se precisar
const bootstrap = window.bootstrap;

// ==================== HELPERS ==================
const roleToType = (role) => (role === "assistant" ? "outgoing" : role === "user" ? "incoming" : "system");

function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return (text || "").replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
}

function hhmm(d = new Date()) {
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

function setActiveInList(id) {
  document.querySelectorAll(".conversation-item").forEach(el => el.classList.remove("active"));
  const el = document.querySelector(`[data-id="${CSS.escape(id)}"]`);
  if (el) el.classList.add("active");
}

// ==================== RENDER ===================
function renderConversations() {
  conversationList.innerHTML = contacts.map(c => `
    <div class="conversation-item ${c.pinned ? "pinned" : ""}" data-id="${c.id}">
      <div class="conversation-avatar ${c.online ? "online" : ""}">
        <img src="${c.avatar || DEFAULT_AVATAR}" alt="${c.name}" class="avatar-img">
      </div>
      <div class="conversation-info">
        <div class="conversation-header">
          <span class="conversation-name">${c.name}</span>
          <span class="conversation-time">${c.time || ""}</span>
        </div>
        <div class="conversation-preview">
          <span class="conversation-message">${c.lastMessage || ""}</span>
          <div class="conversation-meta">
            ${c.muted ? '<i class="bi bi-mic-mute-fill icon-muted"></i>' : ""}
            ${c.pinned ? '<i class="bi bi-pin-fill icon-pinned"></i>' : ""}
            ${c.unread > 0 ? `<span class="badge-unread">${c.unread}</span>` : ""}
          </div>
        </div>
      </div>
    </div>
  `).join("");
  if (currentChatId) setActiveInList(currentChatId);
}

function renderMessages(contactId) {
  const messages = cacheMessages[contactId] || [];

  if (!messages.length) {
    messagesArea.innerHTML = `
      <div class="date-divider"><span class="date-label">Hoje</span></div>
      <div class="text-center text-muted mt-5">
        <p>Nenhuma mensagem ainda. Envie uma mensagem para começar a conversa!</p>
      </div>`;
    return;
  }

  messagesArea.innerHTML = `
    <div class="date-divider"><span class="date-label">Hoje</span></div>
    ${messages.map(renderMessage).join("")}
  `;
}

function renderMessage(msg) {
  let content = "";

  if (msg.quote) {
    content += `
      <div class="message-quote">
        <div class="quote-author">${msg.quote.author}</div>
        <div class="quote-text">${msg.quote.text}</div>
      </div>`;
  }

  if (msg.image)  content += `<img src="${msg.image}" class="message-image" onclick="openImageModal('${msg.image}')">`;
  if (msg.audio)  content += `<div class="message-audio"><audio controls class="audio-player"><source src="${msg.audio}" type="audio/mpeg"></audio></div>`;
  if (msg.linkPreview) {
    const lp = msg.linkPreview;
    content += `
      <div class="message-link-preview">
        <img src="${lp.image}" class="link-preview-image">
        <div class="link-preview-content">
          <div class="link-preview-title">${lp.title}</div>
          <div class="link-preview-description">${lp.description}</div>
          <div class="link-preview-url">${lp.url}</div>
        </div>
      </div>`;
  }

  content += `<div class="message-content">${linkify(msg.content)}</div>`;

  const isOutgoing = msg.type === "outgoing";
  const readClass  = msg.status === "read" ? "read" : "";
  const icon       = msg.status === "double-check" ? "bi-check-all" : "bi-check";

  return `
    <div class="message ${msg.type}" oncontextmenu="showContextMenu(event)">
      <div class="message-bubble">
        ${content}
        <div class="message-meta">
          <span class="message-time">${msg.time || hhmm()}</span>
          ${isOutgoing ? `<span class="message-status ${readClass}"><i class="bi ${icon}"></i></span>` : ""}
        </div>
      </div>
    </div>`;
}

// ==================== DATA =====================
async function loadConversations() {
  try {
    const res = await fetch("/admin/conversas");
    const data = await res.json();

      contacts = (data || []).map(d => {
        const id = String(d.user_id);
        const hist = d.mensagens || [];
        const ultimaMsg = hist.length ? hist[hist.length - 1].content : "";
        return {
          id,
          name: id,
          lastMessage: ultimaMsg,
          time: hhmm(),
          unread: 0,
          avatar: DEFAULT_AVATAR,
          online: true,
        };
      });

    const prev = new Map(contacts.map(c => [c.id, c])); // preservar infos visuais

    contacts = (data || []).map(d => {
      const id = String(d.user_id);
      const was = prev.get(id) || {};
      return {
        id,
        name: id,
        lastMessage: d.ultima || was.lastMessage || "",
        time: d.hora || was.time || "",
        unread: was.unread || 0,
        avatar: was.avatar || DEFAULT_AVATAR,
        online: true,
        pinned: was.pinned || false,
        muted: was.muted || false,
      };
    });

    renderConversations();

    // se nada aberto ainda, abre a primeira
    if (!currentChatId && contacts.length) {
      openChat(contacts[0].id);
    }
  } catch (e) {
    console.error("Erro ao carregar conversas:", e);
  }
}

async function refreshCurrentChat() {
  if (!currentChatId) return;
  try {
    const resp = await fetch(`/admin/conversa/${encodeURIComponent(currentChatId)}`);
    const conv = await resp.json(); // { mensagens: [{role, content, ...}], ... }

    const msgs = (conv.mensagens || []).map(m => ({
      type: roleToType(m.role),
      content: m.content,
      time: m.hora || hhmm(),
      status: "read",
    }));

    cacheMessages[currentChatId] = msgs;
    renderMessages(currentChatId);
    messagesArea.scrollTop = messagesArea.scrollHeight;

    // atualiza header e preview lateral
    const c = contacts.find(x => x.id === currentChatId);
    if (c) {
      c.lastMessage = msgs.length ? msgs[msgs.length - 1].content.slice(0, 60) : c.lastMessage;
      c.time = msgs.length ? msgs[msgs.length - 1].time : hhmm();
      chatName.textContent = c.name;
      chatAvatar.src = c.avatar || DEFAULT_AVATAR;
      chatStatus.textContent = "online";
      renderConversations();
    }
  } catch (e) {
    console.error("Erro ao atualizar conversa:", e);
  }
}

// ==================== OPEN CHAT =====================
async function openChat(contactId) {
  currentChatId = contactId;

  // alterna visibilidade
  document.getElementById("emptyState").classList.add("d-none");
  document.getElementById("chatContainer").classList.remove("d-none");

  setActiveInList(contactId);

  // carrega histórico
  await refreshCurrentChat();

  // garante que a área de mensagens role até o fim
  messagesArea.scrollTop = messagesArea.scrollHeight;

  // em telas pequenas, oculta lista lateral
  sidebarColumn.classList.add("hide-mobile");
  chatColumn.classList.remove("hide-mobile");
}


// ==================== SEND =====================
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || !currentChatId) return;

  const temp = {
    tempId: `tmp-${Date.now()}`,
    type: "outgoing",
    content: text,
    time: hhmm(),
    status: "single-check",
  };
  if (!cacheMessages[currentChatId]) cacheMessages[currentChatId] = [];
  cacheMessages[currentChatId].push(temp);
  messagesArea.insertAdjacentHTML("beforeend", renderMessage(temp));
  messageInput.value = "";
  messagesArea.scrollTop = messagesArea.scrollHeight;

  try {
    await fetch("/admin/enviar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: currentChatId, mensagem: text }),
    });

    // ✅ Ao atualizar, remova o temporário primeiro
    cacheMessages[currentChatId] = cacheMessages[currentChatId].filter(m => !m.tempId);
    await refreshCurrentChat();
  } catch (e) {
    console.error("Erro ao enviar mensagem:", e);
  }
}


// ==================== UX / MISC =================
function autoResizeTextarea() {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + "px";
}

function toggleTheme() {
  document.body.classList.toggle("dark-mode");
  const isDark = document.body.classList.contains("dark-mode");
  themeToggle.querySelector("i").className = isDark ? "bi bi-moon-fill" : "bi bi-sun-fill";
  localStorage.setItem("theme", isDark ? "dark" : "light");
}

function loadThemePreference() {
  const saved = localStorage.getItem("theme") || "dark";
  if (saved === "light") {
    document.body.classList.remove("dark-mode");
    themeToggle.querySelector("i").className = "bi bi-sun-fill";
  }
}

function goBackToList() {
  sidebarColumn.classList.remove("hide-mobile");
  chatColumn.classList.add("hide-mobile");
}

function scrollToBottom() {
  messagesArea.scrollTo({ top: messagesArea.scrollHeight, behavior: "smooth" });
  scrollBottomBtn.classList.add("d-none");
}

function checkScrollPosition() {
  const nearBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 100;
  scrollBottomBtn.classList.toggle("d-none", nearBottom);
}

function showContextMenu(e) {
  e.preventDefault();
  contextMenu.style.left = e.pageX + "px";
  contextMenu.style.top  = e.pageY + "px";
  contextMenu.classList.remove("d-none");
}
function hideContextMenu() { contextMenu.classList.add("d-none"); }

function openImageModal(src) {
  const modal = new bootstrap.Modal(document.getElementById("imageModal"));
  document.getElementById("modalImage").src = src;
  modal.show();
}

// ==================== EVENTS ===================
function setupEventListeners() {
  // clique na lista
  conversationList.addEventListener("click", (e) => {
    const item = e.target.closest(".conversation-item");
    if (!item) return;
    const id = (item.dataset.id || "").trim();
    if (!id || id === "undefined") return; // evita /undefined
    openChat(id);
  });

  // enviar
  sendBtn.addEventListener("click", sendMessage);
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  messageInput.addEventListener("input", autoResizeTextarea);

  // tema
  themeToggle.addEventListener("click", toggleTheme);

  // mobile
  backToList.addEventListener("click", goBackToList);

  // scroll
  scrollBottomBtn.addEventListener("click", scrollToBottom);
  messagesArea.addEventListener("scroll", checkScrollPosition);

  // context menu
  document.addEventListener("click", (e) => { if (!contextMenu.contains(e.target)) hideContextMenu(); });
  contextMenu.addEventListener("click", (e) => {
    const it = e.target.closest(".context-menu-item");
    if (it) { console.log("Context:", it.textContent.trim()); hideContextMenu(); }
  });
}

// ==================== POLLING ==================
let chatsPoll = null;
let listPoll  = null;

function startPolling() {
  if (listPoll)  clearInterval(listPoll);
  if (chatsPoll) clearInterval(chatsPoll);
  listPoll  = setInterval(loadConversations, 15000); // lista lateral
  chatsPoll = setInterval(refreshCurrentChat, 15000); // conversa aberta
}

// ==================== INIT =====================
async function init() {
  setupEventListeners();
  loadThemePreference();
  await loadConversations();      // popula a lista e abre a primeira se houver
  await refreshCurrentChat();     // garante histórico visível sem enviar nada
  startPolling();                 // atualizações contínuas
}
init();
