const STORAGE_KEY = "jobsRagConversations";
const CURRENT_KEY = "jobsRagCurrentConversation";

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("newChatBtn");
const conversationListEl = document.getElementById("conversationList");

let conversations = readConversationList();
let activeConversationId = localStorage.getItem(CURRENT_KEY);
let sending = false;

function readConversationList() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(stored)
      ? stored.filter((item) => item && typeof item.id === "string")
      : [];
  } catch {
    return [];
  }
}

function saveConversationList() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

function setNotice(text) {
  messagesEl.replaceChildren();
  const notice = document.createElement("p");
  notice.className = "empty-state";
  notice.textContent = text;
  messagesEl.appendChild(notice);
}

function appendMessage(text, role = "assistant", sources = []) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role === "user" ? "user" : role === "notice" ? "notice" : "bot"}`;
  bubble.textContent = text;

  if (Array.isArray(sources) && sources.length) {
    const sourceWrap = document.createElement("div");
    sourceWrap.className = "sources";
    const title = document.createElement("div");
    title.className = "sources-title";
    title.textContent = "Sources:";
    sourceWrap.appendChild(title);
    const list = document.createElement("ul");
    for (const source of sources) {
      const item = document.createElement("li");
      item.textContent = source;
      list.appendChild(item);
    }
    sourceWrap.appendChild(list);
    bubble.appendChild(sourceWrap);
  }

  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderConversations() {
  conversationListEl.replaceChildren();
  for (const conversation of conversations) {
    const row = document.createElement("div");
    row.className = "conversation-row";
    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = `conversation-item${conversation.id === activeConversationId ? " active" : ""}`;
    openButton.textContent = conversation.title || "New chat";
    openButton.title = conversation.title || "New chat";
    openButton.addEventListener("click", () => openConversation(conversation.id));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "delete-conversation";
    deleteButton.textContent = "×";
    deleteButton.setAttribute("aria-label", `Delete ${conversation.title || "conversation"}`);
    deleteButton.addEventListener("click", () => deleteConversation(conversation.id));
    row.append(openButton, deleteButton);
    conversationListEl.appendChild(row);
  }
}

async function createConversation() {
  const response = await fetch("/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error(`Could not create conversation (${response.status})`);
  const conversation = await response.json();
  conversations.unshift({ id: conversation.id, title: conversation.title });
  activeConversationId = conversation.id;
  localStorage.setItem(CURRENT_KEY, activeConversationId);
  saveConversationList();
  renderConversations();
  messagesEl.replaceChildren();
  inputEl.focus();
}

async function openConversation(id) {
  activeConversationId = id;
  localStorage.setItem(CURRENT_KEY, id);
  renderConversations();
  setNotice("Loading conversation…");
  try {
    const response = await fetch(`/conversations/${encodeURIComponent(id)}/messages`);
    if (response.status === 404) {
      removeLocalConversation(id);
      setNotice("This conversation is no longer available. Start a new chat.");
      return;
    }
    if (!response.ok) throw new Error(`Could not load conversation (${response.status})`);
    const messages = await response.json();
    if (activeConversationId !== id) return;
    messagesEl.replaceChildren();
    for (const message of messages) appendMessage(message.content, message.role);
    if (!messages.length) setNotice("Ask a question to begin this conversation.");
  } catch (error) {
    console.error("Could not load conversation:", error);
    setNotice("Could not load this conversation. Please try again.");
  }
}

function removeLocalConversation(id) {
  conversations = conversations.filter((item) => item.id !== id);
  saveConversationList();
  renderConversations();
  if (activeConversationId === id) {
    activeConversationId = null;
    localStorage.removeItem(CURRENT_KEY);
  }
}

async function deleteConversation(id) {
  if (!window.confirm("Delete this conversation and its messages?")) return;
  try {
    const response = await fetch(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!response.ok && response.status !== 404) throw new Error(`Delete failed (${response.status})`);
    const wasActive = activeConversationId === id;
    removeLocalConversation(id);
    if (wasActive) {
      if (conversations.length) await openConversation(conversations[0].id);
      else setNotice("Start a new chat to begin.");
    }
  } catch (error) {
    console.error("Could not delete conversation:", error);
    window.alert("Could not delete this conversation. Please try again.");
  }
}

async function sendMessage() {
  const content = inputEl.value.trim();
  if (!content || sending || !activeConversationId) return;
  const conversationId = activeConversationId;

  appendMessage(content, "user");
  inputEl.value = "";
  const loading = document.createElement("div");
  loading.className = "message bot";
  loading.textContent = "Thinking…";
  messagesEl.appendChild(loading);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  sending = true;
  sendBtn.disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, message: content }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    loading.remove();
    if (activeConversationId === conversationId) {
      appendMessage(data.reply || "(Empty reply)", "assistant", data.sources || []);
    }
    const item = conversations.find((conversation) => conversation.id === conversationId);
    if (item) item.title = data.title || item.title;
    conversations = [
      ...conversations.filter((conversation) => conversation.id === conversationId),
      ...conversations.filter((conversation) => conversation.id !== conversationId),
    ];
    saveConversationList();
    renderConversations();
  } catch (error) {
    console.error("Request failed:", error);
    loading.remove();
    if (activeConversationId === conversationId) {
      appendMessage("I couldn't complete that request. Please try again.", "notice");
    }
  } finally {
    sending = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

newChatBtn.addEventListener("click", async () => {
  try {
    await createConversation();
  } catch (error) {
    console.error("Could not create conversation:", error);
    window.alert("Could not start a new chat. Please try again.");
  }
});
sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

async function initialize() {
  renderConversations();
  if (activeConversationId && conversations.some((item) => item.id === activeConversationId)) {
    await openConversation(activeConversationId);
  } else if (conversations.length) {
    await openConversation(conversations[0].id);
  } else {
    try {
      await createConversation();
    } catch (error) {
      console.error("Could not initialize chat:", error);
      setNotice("Could not connect to the chat service. Please refresh to try again.");
    }
  }
}

initialize();
