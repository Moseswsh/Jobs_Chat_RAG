// Config: backend API base URL
// Since frontend and backend are deployed on the same domain, use relative path
// If frontend and backend are deployed separately, change to full URL, e.g.: const API_BASE_URL = "https://jobs-rag-demo.onrender.com";
const API_BASE_URL = "";

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");

// Append a message to the chat window
function appendMessage(text, role = "bot", sources = null) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = text;

  // If sources exist, show them
  if (Array.isArray(sources) && sources.length > 0) {
    const srcWrap = document.createElement("div");
    srcWrap.className = "sources";
    const title = document.createElement("div");
    title.className = "sources-title";
    title.textContent = "Sources:";
    srcWrap.appendChild(title);

    const list = document.createElement("ul");
    for (const item of sources) {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    }
    srcWrap.appendChild(list);
    bubble.appendChild(srcWrap);
  }

  messagesEl.appendChild(bubble);
  scrollToBottom();
}

// Scroll to bottom to keep latest message visible
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Send message to backend
async function sendMessage() {
  const content = inputEl.value.trim();
  if (!content) return;

  // Render user message first
  appendMessage(content, "user");
  inputEl.value = "";

  // Render loading placeholder
  const loadingId = `loading-${Date.now()}`;
  const loading = document.createElement("div");
  loading.id = loadingId;
  loading.className = "message bot";
  loading.textContent = "Thinking...";
  messagesEl.appendChild(loading);
  scrollToBottom();

  sendBtn.disabled = true;

  try {
    // Send request
    // Use relative path /chat since frontend and backend are deployed on the same domain
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: content }),
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const data = await resp.json();

    // Update UI: remove loading, append bot reply
    loading.remove();
    appendMessage(data.reply || "(Empty reply)", "bot", data.sources || []);
  } catch (err) {
    console.error("Request failed:", err);
    loading.remove();
    appendMessage("(System error, please try again later)", "bot");
  } finally {
    sendBtn.disabled = false;
    scrollToBottom();
  }
}

// Bind button event
sendBtn.addEventListener("click", sendMessage);

// Bind keyboard event: Enter to send, Shift+Enter for newline
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
