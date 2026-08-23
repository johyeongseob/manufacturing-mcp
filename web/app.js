const form = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
const clearButton = document.querySelector("#clear-chat");
const welcomeMessage = document.querySelector(".welcome-message");
const architectureNodes = [...document.querySelectorAll("[data-stage]")];

function setArchitectureStage(stage) {
  architectureNodes.forEach((node) => {
    node.classList.toggle("active", Number(node.dataset.stage) === stage);
  });
}

function scrollToLatest() {
  messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
}

function appendUserMessage(text) {
  const article = document.createElement("article");
  article.className = "message user-message";

  const body = document.createElement("div");
  body.className = "message-body";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  body.append(paragraph);
  article.append(body);
  messages.append(article);
  scrollToLatest();
}

function createAssistantMessage(route = null, extraClass = "") {
  const article = document.createElement("article");
  article.className = `message assistant-message ${extraClass}`.trim();

  const avatar = document.createElement("div");
  avatar.className = "agent-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "M";

  const body = document.createElement("div");
  body.className = "message-body";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const name = document.createElement("strong");
  name.textContent = "Manufacturing Agent";
  meta.append(name);

  if (route) {
    const badge = document.createElement("span");
    badge.className = `route-badge ${route}`;
    badge.textContent = route.toUpperCase();
    meta.append(badge);
  }

  body.append(meta);
  article.append(avatar, body);
  messages.append(article);
  return { article, body };
}

function appendLoadingMessage() {
  const { article, body } = createAssistantMessage();
  article.dataset.loading = "true";
  const dots = document.createElement("div");
  dots.className = "loading-dots";
  dots.setAttribute("aria-label", "답변을 생성하고 있습니다");
  dots.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  body.append(dots);
  scrollToLatest();
  return article;
}

function parseTableRow(line) {
  return line
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isSeparatorRow(line) {
  const cells = parseTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{2,}:?$/.test(cell));
}

function appendParagraph(container, lines) {
  const text = lines.join("\n").trim();
  if (!text) return;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  container.append(paragraph);
}

function renderAnswer(container, text) {
  const lines = text.split(/\r?\n/);
  let paragraphLines = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const nextLine = lines[index + 1] ?? "";
    if (line.includes("|") && isSeparatorRow(nextLine)) {
      appendParagraph(container, paragraphLines);
      paragraphLines = [];

      const headers = parseTableRow(line);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|")) {
        rows.push(parseTableRow(lines[index]));
        index += 1;
      }
      index -= 1;

      const wrapper = document.createElement("div");
      wrapper.className = "answer-table-wrap";
      const table = document.createElement("table");
      table.className = "answer-table";
      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      headers.forEach((header) => {
        const cell = document.createElement("th");
        cell.textContent = header;
        headerRow.append(cell);
      });
      thead.append(headerRow);

      const tbody = document.createElement("tbody");
      rows.forEach((row) => {
        const tableRow = document.createElement("tr");
        row.forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          tableRow.append(cell);
        });
        tbody.append(tableRow);
      });
      table.append(thead, tbody);
      wrapper.append(table);
      container.append(wrapper);
    } else if (line.trim()) {
      paragraphLines.push(line);
    } else {
      appendParagraph(container, paragraphLines);
      paragraphLines = [];
    }
  }
  appendParagraph(container, paragraphLines);
}

function appendAnswer(text, route) {
  const { body } = createAssistantMessage(route);
  renderAnswer(body, text);
  scrollToLatest();
}

function appendError(text) {
  const { body } = createAssistantMessage(null, "error-message");
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  body.append(paragraph);
  scrollToLatest();
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  questionInput.disabled = isLoading;
  sendButton.querySelector("span:first-child").textContent = isLoading ? "분석 중" : "질문 보내기";
}

async function askQuestion(question) {
  appendUserMessage(question);
  const loadingMessage = appendLoadingMessage();
  setLoading(true);
  setArchitectureStage(1);
  const backendStageTimer = window.setTimeout(() => setArchitectureStage(2), 700);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 2 }),
    });
    const payload = await response.json();
    loadingMessage.remove();
    if (!response.ok) {
      throw new Error(payload.detail ?? "요청을 처리하지 못했습니다.");
    }
    setArchitectureStage(2);
    appendAnswer(payload.answer, payload.route);
  } catch (error) {
    loadingMessage.remove();
    setArchitectureStage(1);
    appendError(error.message || "서버 연결을 확인해 주세요.");
  } finally {
    window.clearTimeout(backendStageTimer);
    setArchitectureStage(-1);
    setLoading(false);
    questionInput.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || sendButton.disabled) return;
  questionInput.value = "";
  questionInput.style.height = "auto";
  await askQuestion(question);
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

questionInput.addEventListener("input", () => {
  if (!questionInput.disabled) {
    setArchitectureStage(questionInput.value.trim() ? 0 : -1);
  }
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 130)}px`;
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.dispatchEvent(new Event("input"));
    questionInput.focus();
  });
});

clearButton.addEventListener("click", () => {
  messages.replaceChildren(welcomeMessage.cloneNode(true));
  setArchitectureStage(-1);
  questionInput.focus();
});
