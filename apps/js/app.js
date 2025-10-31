// Mock Data
const contacts = [
  {
    id: 1,
    name: "Maria Silva",
    avatar: "https://i.pravatar.cc/150?img=5",
    lastMessage: "Oi! Tudo bem?",
    time: "10:30",
    unread: 3,
    online: true,
    pinned: true,
    muted: false,
  },
  {
    id: 2,
    name: "João Santos",
    avatar: "https://i.pravatar.cc/150?img=12",
    lastMessage: "Vamos marcar aquele café?",
    time: "09:15",
    unread: 0,
    online: false,
    pinned: true,
    muted: false,
  },
  {
    id: 3,
    name: "Ana Costa",
    avatar: "https://i.pravatar.cc/150?img=9",
    lastMessage: "Obrigada pela ajuda! 😊",
    time: "Ontem",
    unread: 0,
    online: true,
    pinned: false,
    muted: false,
  },
  {
    id: 4,
    name: "Grupo Trabalho",
    avatar: "https://i.pravatar.cc/150?img=20",
    lastMessage: "Pedro: Reunião às 15h",
    time: "Ontem",
    unread: 12,
    online: false,
    pinned: false,
    muted: true,
  },
  {
    id: 5,
    name: "Carlos Oliveira",
    avatar: "https://i.pravatar.cc/150?img=15",
    lastMessage: "Enviou uma foto",
    time: "14/10",
    unread: 0,
    online: false,
    pinned: false,
    muted: false,
  },
  {
    id: 6,
    name: "Beatriz Lima",
    avatar: "https://i.pravatar.cc/150?img=24",
    lastMessage: "Você: Perfeito! Até logo",
    time: "13/10",
    unread: 0,
    online: true,
    pinned: false,
    muted: false,
  },
  {
    id: 7,
    name: "Família ❤️",
    avatar: "https://i.pravatar.cc/150?img=30",
    lastMessage: "Mãe: Jantar domingo?",
    time: "12/10",
    unread: 5,
    online: false,
    pinned: false,
    muted: false,
  },
  {
    id: 8,
    name: "Rafael Mendes",
    avatar: "https://i.pravatar.cc/150?img=33",
    lastMessage: "Beleza! Combinado então",
    time: "11/10",
    unread: 0,
    online: false,
    pinned: false,
    muted: false,
  },
  {
    id: 9,
    name: "Juliana Rocha",
    avatar: "https://i.pravatar.cc/150?img=44",
    lastMessage: "Enviou um áudio",
    time: "10/10",
    unread: 1,
    online: false,
    pinned: false,
    muted: false,
  },
  {
    id: 10,
    name: "Amigos da Faculdade",
    avatar: "https://i.pravatar.cc/150?img=50",
    lastMessage: "Lucas: 😂😂😂",
    time: "09/10",
    unread: 0,
    online: false,
    pinned: false,
    muted: true,
  },
  {
    id: 11,
    name: "Fernando Alves",
    avatar: "https://i.pravatar.cc/150?img=60",
    lastMessage: "Você: Vou verificar e te aviso",
    time: "08/10",
    unread: 0,
    online: false,
    pinned: false,
    muted: false,
  },
  {
    id: 12,
    name: "Patrícia Souza",
    avatar: "https://i.pravatar.cc/150?img=47",
    lastMessage: "Ótima notícia! 🎉",
    time: "07/10",
    unread: 0,
    online: true,
    pinned: false,
    muted: false,
  },
]

const mockMessages = {
  1: [
    {
      type: "incoming",
      content: "Oi! Tudo bem?",
      time: "10:25",
      status: "read",
    },
    {
      type: "incoming",
      content:
        "Conseguiu ver aquele documento que te enviei ontem? Preciso da sua opinião sobre alguns pontos importantes antes da reunião de amanhã.",
      time: "10:26",
      status: "read",
    },
    {
      type: "outgoing",
      content: "Oi Maria! Tudo ótimo, e você?",
      time: "10:28",
      status: "double-check",
    },
    {
      type: "outgoing",
      content: "Sim, já dei uma olhada. Achei muito bom! Vou preparar alguns comentários e te envio ainda hoje.",
      time: "10:28",
      status: "double-check",
    },
    {
      type: "incoming",
      content: "Perfeito! Muito obrigada 😊",
      time: "10:30",
      status: "read",
    },
    {
      type: "incoming",
      quote: {
        author: "Você",
        text: "Vou preparar alguns comentários",
      },
      content: "Pode ser até às 18h?",
      time: "10:30",
      status: "read",
    },
    {
      type: "outgoing",
      content: "Claro! Sem problemas 👍",
      time: "10:31",
      status: "single-check",
    },
  ],
}

// State
let currentChatId = null
const typingTimeout = null

// DOM Elements
const conversationList = document.querySelector(".conversation-list")
const emptyState = document.getElementById("emptyState")
const chatContainer = document.getElementById("chatContainer")
const messagesArea = document.getElementById("messagesArea")
const messageInput = document.getElementById("messageInput")
const sendBtn = document.getElementById("sendBtn")
const chatName = document.getElementById("chatName")
const chatStatus = document.getElementById("chatStatus")
const chatAvatar = document.getElementById("chatAvatar")
const themeToggle = document.getElementById("themeToggle")
const backToList = document.getElementById("backToList")
const scrollBottomBtn = document.getElementById("scrollBottomBtn")
const contextMenu = document.getElementById("contextMenu")
const sidebarColumn = document.getElementById("sidebarColumn")
const chatColumn = document.getElementById("chatColumn")

// Bootstrap Modal Initialization
const bootstrap = window.bootstrap

// Initialize
function init() {
  renderConversations()
  setupEventListeners()
  loadThemePreference()
}

// Render Conversations
function renderConversations() {
  conversationList.innerHTML = contacts
    .map(
      (contact) => `
    <div class="conversation-item ${contact.pinned ? "pinned" : ""}" data-id="${contact.id}">
      <div class="conversation-avatar ${contact.online ? "online" : ""}">
        <img src="${contact.avatar}" alt="${contact.name}" class="avatar-img">
      </div>
      <div class="conversation-info">
        <div class="conversation-header">
          <span class="conversation-name">${contact.name}</span>
          <span class="conversation-time">${contact.time}</span>
        </div>
        <div class="conversation-preview">
          <span class="conversation-message">${contact.lastMessage}</span>
          <div class="conversation-meta">
            ${contact.muted ? '<i class="bi bi-mic-mute-fill icon-muted"></i>' : ""}
            ${contact.pinned ? '<i class="bi bi-pin-fill icon-pinned"></i>' : ""}
            ${contact.unread > 0 ? `<span class="badge-unread">${contact.unread}</span>` : ""}
          </div>
        </div>
      </div>
    </div>
  `,
    )
    .join("")
}

// Open Chat
function openChat(contactId) {
  currentChatId = contactId
  const contact = contacts.find((c) => c.id === contactId)

  if (!contact) return

  // Update active state
  document.querySelectorAll(".conversation-item").forEach((item) => {
    item.classList.remove("active")
  })
  document.querySelector(`[data-id="${contactId}"]`).classList.add("active")

  // Update chat header
  chatName.textContent = contact.name
  chatStatus.textContent = contact.online ? "online" : "visto por último hoje às 09:30"
  chatAvatar.src = contact.avatar
  chatAvatar.alt = contact.name

  // Show chat container
  emptyState.classList.add("d-none")
  chatContainer.classList.remove("d-none")

  // Render messages
  renderMessages(contactId)

  // Scroll to bottom
  setTimeout(() => {
    messagesArea.scrollTop = messagesArea.scrollHeight
  }, 100)

  // Mobile: hide sidebar, show chat
  if (window.innerWidth < 768) {
    sidebarColumn.classList.add("hide-mobile")
    chatColumn.classList.remove("hide-mobile")
  }

  // Simulate typing indicator
  setTimeout(() => {
    showTypingIndicator()
  }, 2000)
}

// Render Messages
function renderMessages(contactId) {
  const messages = mockMessages[contactId] || []

  if (messages.length === 0) {
    messagesArea.innerHTML = `
      <div class="date-divider">
        <span class="date-label">Hoje</span>
      </div>
      <div class="text-center text-muted mt-5">
        <p>Nenhuma mensagem ainda. Envie uma mensagem para começar a conversa!</p>
      </div>
    `
    return
  }

  messagesArea.innerHTML = `
    <div class="date-divider">
      <span class="date-label">Hoje</span>
    </div>
    ${messages.map((msg) => renderMessage(msg)).join("")}
  `
}

// Render Single Message
function renderMessage(msg) {
  let content = ""

  if (msg.quote) {
    content += `
      <div class="message-quote">
        <div class="quote-author">${msg.quote.author}</div>
        <div class="quote-text">${msg.quote.text}</div>
      </div>
    `
  }

  if (msg.image) {
    content += `<img src="${msg.image}" alt="Imagem" class="message-image" onclick="openImageModal('${msg.image}')">`
  }

  if (msg.audio) {
    content += `
      <div class="message-audio">
        <audio controls class="audio-player">
          <source src="${msg.audio}" type="audio/mpeg">
        </audio>
      </div>
    `
  }

  if (msg.sticker) {
    return `
      <div class="message ${msg.type}">
        <div class="message-bubble message-sticker">
          <img src="${msg.sticker}" alt="Sticker" class="sticker-img">
        </div>
      </div>
    `
  }

  if (msg.linkPreview) {
    content += `
      <div class="message-link-preview">
        <img src="${msg.linkPreview.image}" alt="Preview" class="link-preview-image">
        <div class="link-preview-content">
          <div class="link-preview-title">${msg.linkPreview.title}</div>
          <div class="link-preview-description">${msg.linkPreview.description}</div>
          <div class="link-preview-url">${msg.linkPreview.url}</div>
        </div>
      </div>
    `
  }

  content += `<div class="message-content">${linkify(msg.content)}</div>`

  const statusIcon = msg.status === "double-check" ? '<i class="bi bi-check-all"></i>' : '<i class="bi bi-check"></i>'

  const statusClass = msg.status === "read" ? "read" : ""

  return `
    <div class="message ${msg.type}" oncontextmenu="showContextMenu(event)">
      <div class="message-bubble">
        ${content}
        <div class="message-meta">
          <span class="message-time">${msg.time}</span>
          ${msg.type === "outgoing" ? `<span class="message-status ${statusClass}">${statusIcon}</span>` : ""}
        </div>
      </div>
    </div>
  `
}

// Linkify text
function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g
  return text.replace(urlRegex, '<a href="$1" target="_blank">$1</a>')
}

// Send Message
function sendMessage() {
  const text = messageInput.value.trim()

  if (!text || !currentChatId) return

  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`

  const newMessage = {
    type: "outgoing",
    content: text,
    time: time,
    status: "single-check",
  }

  // Add to mock data
  if (!mockMessages[currentChatId]) {
    mockMessages[currentChatId] = []
  }
  mockMessages[currentChatId].push(newMessage)

  // Render new message
  const messageHtml = renderMessage(newMessage)
  messagesArea.insertAdjacentHTML("beforeend", messageHtml)

  // Clear input
  messageInput.value = ""
  messageInput.style.height = "auto"

  // Scroll to bottom
  messagesArea.scrollTop = messagesArea.scrollHeight

  // Update conversation preview
  const contact = contacts.find((c) => c.id === currentChatId)
  if (contact) {
    contact.lastMessage = `Você: ${text.substring(0, 30)}${text.length > 30 ? "..." : ""}`
    contact.time = time
    renderConversations()
    document.querySelector(`[data-id="${currentChatId}"]`).classList.add("active")
  }

  // Simulate double check after 1 second
  setTimeout(() => {
    const lastMessage = messagesArea.querySelector(".message.outgoing:last-child .message-status")
    if (lastMessage) {
      lastMessage.innerHTML = '<i class="bi bi-check-all"></i>'
      lastMessage.classList.add("read")
    }
  }, 1000)
}

// Auto-resize textarea
function autoResizeTextarea() {
  messageInput.style.height = "auto"
  const newHeight = Math.min(messageInput.scrollHeight, 150)
  messageInput.style.height = newHeight + "px"
}

// Show Typing Indicator
function showTypingIndicator() {
  chatStatus.textContent = "digitando..."
  chatStatus.classList.add("typing")

  setTimeout(() => {
    chatStatus.textContent = "online"
    chatStatus.classList.remove("typing")
  }, 3000)
}

// Theme Toggle
function toggleTheme() {
  document.body.classList.toggle("dark-mode")
  const isDark = document.body.classList.contains("dark-mode")

  themeToggle.querySelector("i").className = isDark ? "bi bi-moon-fill" : "bi bi-sun-fill"

  // Save preference
  localStorage.setItem("theme", isDark ? "dark" : "light")
}

function loadThemePreference() {
  const savedTheme = localStorage.getItem("theme") || "dark"

  if (savedTheme === "light") {
    document.body.classList.remove("dark-mode")
    themeToggle.querySelector("i").className = "bi bi-sun-fill"
  }
}

// Back to List (Mobile)
function goBackToList() {
  sidebarColumn.classList.remove("hide-mobile")
  chatColumn.classList.add("hide-mobile")
}

// Scroll to Bottom
function scrollToBottom() {
  messagesArea.scrollTo({
    top: messagesArea.scrollHeight,
    behavior: "smooth",
  })
  scrollBottomBtn.classList.add("d-none")
}

// Check Scroll Position
function checkScrollPosition() {
  const isNearBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 100

  if (isNearBottom) {
    scrollBottomBtn.classList.add("d-none")
  } else {
    scrollBottomBtn.classList.remove("d-none")
  }
}

// Context Menu
function showContextMenu(event) {
  event.preventDefault()

  contextMenu.style.left = event.pageX + "px"
  contextMenu.style.top = event.pageY + "px"
  contextMenu.classList.remove("d-none")
}

function hideContextMenu() {
  contextMenu.classList.add("d-none")
}

// Open Image Modal
function openImageModal(src) {
  const modal = new bootstrap.Modal(document.getElementById("imageModal"))
  document.getElementById("modalImage").src = src
  modal.show()
}

// Event Listeners
function setupEventListeners() {
  // Conversation click
  conversationList.addEventListener("click", (e) => {
    const item = e.target.closest(".conversation-item")
    if (item) {
      const contactId = Number.parseInt(item.dataset.id)
      openChat(contactId)
    }
  })

  // Send message
  sendBtn.addEventListener("click", sendMessage)

  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  })

  messageInput.addEventListener("input", autoResizeTextarea)

  // Theme toggle
  themeToggle.addEventListener("click", toggleTheme)

  // Back to list
  backToList.addEventListener("click", goBackToList)

  // Scroll to bottom
  scrollBottomBtn.addEventListener("click", scrollToBottom)

  // Check scroll position
  messagesArea.addEventListener("scroll", checkScrollPosition)

  // Hide context menu on click outside
  document.addEventListener("click", (e) => {
    if (!contextMenu.contains(e.target)) {
      hideContextMenu()
    }
  })

  // Context menu actions
  contextMenu.addEventListener("click", (e) => {
    const item = e.target.closest(".context-menu-item")
    if (item) {
      console.log("Context menu action:", item.textContent.trim())
      hideContextMenu()
    }
  })

  // Simulate connection status
  setTimeout(() => {
    const connectionBar = document.getElementById("connectionBar")
    connectionBar.classList.remove("d-none")
    connectionBar.textContent = "Conectando..."

    setTimeout(() => {
      connectionBar.textContent = "Conectado"
      connectionBar.style.backgroundColor = "#25d366"

      setTimeout(() => {
        connectionBar.classList.add("d-none")
      }, 2000)
    }, 1500)
  }, 1000)
}

// Initialize app
init()
