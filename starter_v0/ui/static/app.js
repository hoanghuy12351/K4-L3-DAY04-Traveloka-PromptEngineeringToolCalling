(() => {
  "use strict";

  const state = {
    meta: null,
    session: null,
    scenarios: [],
    selectedScenario: null,
    scenarioTurn: 0,
    toolTraceCount: 0,
    busy: false,
  };

  const elements = {
    error: document.getElementById("app-error"),
    form: document.getElementById("chat-form"),
    input: document.getElementById("chat-input"),
    send: document.getElementById("send-button"),
    messages: document.getElementById("messages"),
    sessionStatus: document.getElementById("session-status"),
    conversationId: document.getElementById("conversation-id"),
    runtimeMeta: document.getElementById("runtime-meta"),
    advancedRuntimeMeta: document.getElementById("advanced-runtime-meta"),
    transcriptMeta: document.getElementById("transcript-meta"),
    advancedTranscriptMeta: document.getElementById("advanced-transcript-meta"),
    transcriptViewer: document.getElementById("transcript-viewer"),
    traces: document.getElementById("tool-traces"),
    traceEmpty: document.getElementById("trace-empty"),
    registry: document.getElementById("tool-registry"),
    filter: document.getElementById("scenario-filter"),
    scenarioList: document.getElementById("scenario-list"),
    scenarioDetail: document.getElementById("scenario-detail"),
    loadScenario: document.getElementById("load-scenario"),
    nextScenarioTurn: document.getElementById("next-scenario-turn"),
    restartScenario: document.getElementById("restart-scenario"),
    newConversation: document.getElementById("new-conversation"),
    resetConversation: document.getElementById("reset-conversation"),
    viewTranscript: document.getElementById("view-transcript"),
    downloadTranscript: document.getElementById("download-transcript"),
    copyTranscriptId: document.getElementById("copy-transcript-id"),
  };

  const headerValues = {
    provider: document.getElementById("header-provider"),
    model: document.getElementById("header-model"),
    version: document.getElementById("header-version"),
  };

  function setText(node, text) {
    node.textContent = text === null || text === undefined || text === "" ? "Not available" : String(text);
  }

  function prettyJson(value) {
    return JSON.stringify(value, null, 2);
  }

  function showError(message) {
    if (!message) {
      elements.error.hidden = true;
      elements.error.textContent = "";
      return;
    }
    elements.error.hidden = false;
    elements.error.textContent = message;
  }

  async function request(url, options = {}) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error("The local server returned an invalid response.");
    }
    if (!response.ok) {
      throw new Error(payload.error || `Request failed with status ${response.status}.`);
    }
    return payload;
  }

  function metadataRow(list, label, value, className = "") {
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = value === null || value === undefined || value === "" ? "Not available" : String(value);
    if (className) {
      description.className = className;
    }
    list.append(term, description);
  }

  function fileName(path) {
    return String(path || "").split(/[\\/]/).pop() || "Không có";
  }

  function shortId(value, visible = 12) {
    const text = String(value || "");
    if (text.length <= visible + 6) {
      return text || "Không có";
    }
    return `${text.slice(0, visible)}...${text.slice(-6)}`;
  }

  function renderMetadata() {
    if (!state.meta) {
      return;
    }
    setText(headerValues.provider, state.meta.provider);
    setText(headerValues.model, state.meta.model);
    setText(headerValues.version, state.meta.version);

    elements.runtimeMeta.replaceChildren();
    metadataRow(elements.runtimeMeta, "Provider", state.meta.provider);
    metadataRow(elements.runtimeMeta, "Model", state.meta.model);
    metadataRow(elements.runtimeMeta, "Phiên bản", state.meta.version);
    metadataRow(elements.runtimeMeta, "Mã artifact", shortId(state.meta.artifact_version, 18));
    metadataRow(elements.runtimeMeta, "Công cụ", `${state.meta.tool_count} công cụ`);
    metadataRow(elements.runtimeMeta, "Lịch sử", `${state.meta.history_window} lượt gần nhất`);

    elements.advancedRuntimeMeta.replaceChildren();
    metadataRow(elements.advancedRuntimeMeta, "Prompt hash", state.meta.prompt_hash_short);
    metadataRow(elements.advancedRuntimeMeta, "Tools hash", state.meta.tools_hash_short);
    metadataRow(elements.advancedRuntimeMeta, "System prompt", state.meta.system_prompt_path, "wrap-value");
    metadataRow(elements.advancedRuntimeMeta, "Tools file", state.meta.tools_path, "wrap-value");
    metadataRow(elements.advancedRuntimeMeta, "Tool names", state.meta.tool_names.join(", "), "wrap-value");
    metadataRow(elements.advancedRuntimeMeta, "Giới hạn lượt tool", state.meta.max_tool_rounds);
  }

  function renderTranscriptMeta() {
    if (!state.session) {
      return;
    }
    elements.transcriptMeta.replaceChildren();
    metadataRow(elements.transcriptMeta, "Mã phiên", shortId(state.session.session_id));
    metadataRow(elements.transcriptMeta, "Mã bản ghi", shortId(state.session.transcript_id, 18));
    metadataRow(elements.transcriptMeta, "Tệp", fileName(state.session.transcript_path), "wrap-value");
    metadataRow(elements.transcriptMeta, "Lưu gần nhất", state.session.last_saved_at);
    metadataRow(elements.transcriptMeta, "Trạng thái", state.session.saved ? "Đã lưu" : "Lỗi khi lưu");
    if (state.session.transcript_error) {
      metadataRow(elements.transcriptMeta, "Lỗi", state.session.transcript_error, "wrap-value");
    }
    elements.advancedTranscriptMeta.replaceChildren();
    metadataRow(elements.advancedTranscriptMeta, "Session ID", state.session.session_id, "wrap-value");
    metadataRow(elements.advancedTranscriptMeta, "Transcript ID", state.session.transcript_id, "wrap-value");
    metadataRow(elements.advancedTranscriptMeta, "Đường dẫn tệp", state.session.transcript_path, "wrap-value");
    setText(elements.conversationId, `Phiên ${shortId(state.session.session_id, 8)}`);
  }

  function setStatus(label, kind) {
    elements.sessionStatus.textContent = label;
    elements.sessionStatus.className = `status-badge status-${kind}`;
  }

  function setBusy(busy, label = "Thinking") {
    state.busy = busy;
    elements.send.disabled = busy;
    elements.input.disabled = busy;
    if (busy) {
      setStatus(label, "working");
    }
  }

  function appendMessage(role, text, options = {}) {
    const card = document.createElement("article");
    card.className = `message ${role}-message`;
    const roleLabel = document.createElement("p");
    roleLabel.className = "message-role";
    roleLabel.textContent = role === "user" ? "Bạn" : "Trợ lý";
    const body = document.createElement("div");
    body.className = "message-body";
    const paragraph = document.createElement("p");
    paragraph.textContent = text || (options.error ? "Provider không trả về nội dung phản hồi." : "Chưa có nội dung phản hồi.");
    body.appendChild(paragraph);

    if (options.status) {
      const status = document.createElement("span");
      status.className = `inline-status ${options.status === "provider_error" ? "inline-error" : "inline-neutral"}`;
      status.textContent = options.status.replaceAll("_", " ");
      body.appendChild(status);
    }

    if (options.structured) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "Dữ liệu kỹ thuật của phản hồi";
      const code = document.createElement("pre");
      code.textContent = prettyJson(options.structured);
      details.append(summary, code);
      body.appendChild(details);
    }

    if (options.error) {
      const error = document.createElement("pre");
      error.className = "message-error";
      error.textContent = options.error;
      body.appendChild(error);
    }
    card.append(roleLabel, body);
    elements.messages.appendChild(card);
    elements.messages.scrollTop = elements.messages.scrollHeight;
  }

  function clearConversation() {
    elements.messages.replaceChildren();
    appendMessage("assistant", "Phiên mới đã sẵn sàng. Hãy nêu yêu cầu để lưu lại bằng chứng gọi công cụ thực tế.");
    elements.traces.replaceChildren();
    state.toolTraceCount = 0;
    elements.traceEmpty.hidden = false;
    elements.transcriptViewer.hidden = true;
    elements.transcriptViewer.textContent = "";
  }

  function traceState(result) {
    if (result && result.awaiting_user) {
      return { label: "Chờ bổ sung", style: "trace-waiting" };
    }
    if (result && result.error) {
      return { label: "Lỗi", style: "trace-error" };
    }
    return { label: "Thành công", style: "trace-success" };
  }

  function createJsonBlock(label, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "trace-json-group";
    const heading = document.createElement("h4");
    heading.textContent = label;
    const block = document.createElement("pre");
    block.textContent = prettyJson(value);
    wrapper.append(heading, block);
    return wrapper;
  }

  function renderToolTrace(rounds) {
    for (const round of rounds || []) {
      for (const event of round.tool_results || []) {
        const result = event.result || {};
        const status = traceState(result);
        const card = document.createElement("article");
        card.className = `tool-card ${status.style}`;
        const header = document.createElement("div");
        header.className = "tool-card-header";
        const titleBlock = document.createElement("div");
        const roundLabel = document.createElement("p");
        roundLabel.className = "tool-round";
        roundLabel.textContent = `Round ${round.round}`;
        const title = document.createElement("h3");
        title.textContent = event.tool;
        titleBlock.append(roundLabel, title);
        const badge = document.createElement("span");
        badge.className = "trace-badge";
        badge.textContent = status.label;
        header.append(titleBlock, badge);
        card.appendChild(header);
        card.appendChild(createJsonBlock("Tham số", event.args || {}));
        if (result && result.awaiting_user) {
          const question = document.createElement("div");
          question.className = "clarification-question";
          const heading = document.createElement("h4");
          heading.textContent = "Câu hỏi cần bổ sung";
          const content = document.createElement("p");
          content.textContent = result.question || "Công cụ đang chờ thêm thông tin.";
          question.append(heading, content);
          card.appendChild(question);
        }
        card.appendChild(createJsonBlock(result && result.error ? "Chi tiết lỗi" : "Kết quả", result));
        if (event.tool === "create_booking_request") {
          const bookingNotice = document.createElement("p");
          bookingNotice.className = "booking-notice";
          bookingNotice.textContent = "Đây chỉ là yêu cầu đặt chỗ mô phỏng. Không có đặt chỗ hoặc thanh toán thật.";
          card.appendChild(bookingNotice);
        }
        elements.traces.appendChild(card);
        state.toolTraceCount += 1;
      }
    }
    elements.traceEmpty.hidden = state.toolTraceCount > 0;
  }

  function requiredArguments(tool) {
    return (tool.parameters && tool.parameters.required) || [];
  }

  function renderRegistry() {
    if (!state.meta) {
      return;
    }
    elements.registry.replaceChildren();
    for (const tool of state.meta.tool_declarations) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = tool.name;
      const description = document.createElement("p");
      description.textContent = tool.description || "Chưa có mô tả.";
      const required = document.createElement("p");
      required.className = "registry-required";
      required.textContent = `Bắt buộc: ${requiredArguments(tool).join(", ") || "Không có"}`;
      details.append(summary, description, required);
      elements.registry.appendChild(details);
    }
  }

  function categoryLabel(category) {
    const labels = {
      basic_tool: "Công cụ cơ bản",
      missing_info: "Thiếu thông tin",
      multi_tool: "Nhiều công cụ",
      multi_turn: "Nhiều lượt",
      correction: "Sửa thông tin",
      cancel: "Hủy yêu cầu",
      confirmation: "Xác nhận",
      safety: "An toàn",
      meta: "Khả năng hỗ trợ",
    };
    return labels[category] || category.replaceAll("_", " ");
  }

  function filteredScenarios() {
    const filter = elements.filter.value;
    return state.scenarios.filter((scenario) => filter === "all" || scenario.category === filter);
  }

  function renderScenarioList() {
    elements.scenarioList.replaceChildren();
    for (const scenario of filteredScenarios()) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "scenario-item";
      if (state.selectedScenario && state.selectedScenario.id === scenario.id) {
        button.classList.add("selected");
      }
      const title = document.createElement("strong");
      title.textContent = scenario.title;
      const category = document.createElement("span");
      category.textContent = categoryLabel(scenario.category);
      button.append(title, category);
      button.addEventListener("click", () => selectScenario(scenario));
      elements.scenarioList.appendChild(button);
    }
  }

  function renderScenarioDetail() {
    elements.scenarioDetail.replaceChildren();
    const scenario = state.selectedScenario;
    if (!scenario) {
      const text = document.createElement("p");
      text.textContent = "Chọn một tình huống, sau đó nạp từng lượt câu hỏi vào ô chat.";
      elements.scenarioDetail.appendChild(text);
      elements.loadScenario.disabled = true;
      elements.nextScenarioTurn.disabled = true;
      elements.restartScenario.disabled = true;
      return;
    }
    const title = document.createElement("h3");
    title.textContent = scenario.title;
    const expectedLabel = document.createElement("p");
    expectedLabel.className = "detail-label";
    expectedLabel.textContent = "Hành vi mong đợi";
    const expected = document.createElement("p");
    expected.textContent = scenario.expected_behavior;
    const progress = document.createElement("p");
    progress.className = "scenario-progress";
    progress.textContent = `Lượt đang chọn: ${state.scenarioTurn + 1} / ${scenario.turns.length}`;
    elements.scenarioDetail.append(title, expectedLabel, expected, progress);
    elements.loadScenario.disabled = false;
    elements.nextScenarioTurn.disabled = state.scenarioTurn >= scenario.turns.length - 1;
    elements.restartScenario.disabled = false;
  }

  function selectScenario(scenario) {
    state.selectedScenario = scenario;
    state.scenarioTurn = 0;
    renderScenarioList();
    renderScenarioDetail();
  }

  function loadScenarioPrompt() {
    if (!state.selectedScenario) {
      return;
    }
    elements.input.value = state.selectedScenario.turns[state.scenarioTurn] || "";
    elements.input.focus();
  }

  function nextScenarioTurn() {
    if (!state.selectedScenario || state.scenarioTurn >= state.selectedScenario.turns.length - 1) {
      return;
    }
    state.scenarioTurn += 1;
    loadScenarioPrompt();
    renderScenarioDetail();
  }

  function updateSession(session) {
    state.session = session;
    renderTranscriptMeta();
  }

  async function createSession({ clear = true } = {}) {
    const payload = await request("/api/session", { method: "POST" });
    state.meta = payload.meta;
    updateSession(payload.session);
    renderMetadata();
    renderRegistry();
    if (clear) {
      clearConversation();
    }
    setStatus("Sẵn sàng", "idle");
  }

  async function resetSession() {
    if (!state.session || state.busy) {
      return;
    }
    showError("");
    const payload = await request(`/api/session/${state.session.session_id}/reset`, { method: "POST" });
    state.meta = payload.meta;
    updateSession(payload.session);
    renderMetadata();
    clearConversation();
    setStatus("Sẵn sàng", "idle");
  }

  async function sendMessage(message) {
    if (!state.session || state.busy) {
      return;
    }
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }
    showError("");
    appendMessage("user", trimmed);
    elements.input.value = "";
    setBusy(true, "Đang xử lý");
    try {
      const result = await request(`/api/session/${state.session.session_id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: trimmed }),
      });
      updateSession(result.transcript);
      renderToolTrace(result.rounds);
      const reply = result.structured_assistant && result.structured_assistant.reply
        ? result.structured_assistant.reply
        : result.assistant_text;
      appendMessage("assistant", reply, {
        status: result.status,
        structured: result.structured_assistant,
        error: result.error,
      });
      if (result.status === "waiting_for_user") {
        setStatus("Cần bổ sung", "waiting");
      } else if (result.status === "provider_error") {
        setStatus("Lỗi provider", "error");
      } else if (result.status === "max_tool_rounds") {
        setStatus("Đạt giới hạn tool", "error");
      } else {
        setStatus("Đã phản hồi", "success");
      }
    } catch (error) {
      appendMessage("assistant", "Máy chủ cục bộ chưa thể hoàn tất yêu cầu này.", {
        status: "request_error",
        error: error.message,
      });
      setStatus("Lỗi yêu cầu", "error");
    } finally {
      setBusy(false);
      if (elements.sessionStatus.textContent === "Đang xử lý") {
        setStatus("Sẵn sàng", "idle");
      }
      elements.input.focus();
    }
  }

  async function viewTranscript() {
    if (!state.session) {
      return;
    }
    try {
      const transcript = await request(`/api/session/${state.session.session_id}/transcript`);
      elements.transcriptViewer.textContent = prettyJson(transcript);
      elements.transcriptViewer.hidden = !elements.transcriptViewer.hidden;
    } catch (error) {
      showError(error.message);
    }
  }

  async function copyTranscriptId() {
    if (!state.session) {
      return;
    }
    try {
      await navigator.clipboard.writeText(state.session.transcript_id);
      setStatus("Đã sao chép mã", "success");
    } catch (_error) {
      showError("Không thể sao chép tự động. Bạn có thể chọn mã bản ghi trong phần thông tin phiên.");
    }
  }

  function setupScenarioFilter() {
    const categories = [...new Set(state.scenarios.map((scenario) => scenario.category))].sort();
    elements.filter.replaceChildren();
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All categories";
    elements.filter.appendChild(allOption);
    for (const category of categories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = categoryLabel(category);
      elements.filter.appendChild(option);
    }
    elements.filter.addEventListener("change", renderScenarioList);
  }

  function bindEvents() {
    elements.form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(elements.input.value);
    });
    elements.input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        elements.form.requestSubmit();
      }
    });
    elements.newConversation.addEventListener("click", async () => {
      if (!state.busy) {
        try {
          await createSession();
        } catch (error) {
          showError(error.message);
        }
      }
    });
    elements.resetConversation.addEventListener("click", async () => {
      try {
        await resetSession();
      } catch (error) {
        showError(error.message);
      }
    });
    elements.loadScenario.addEventListener("click", loadScenarioPrompt);
    elements.nextScenarioTurn.addEventListener("click", nextScenarioTurn);
    elements.restartScenario.addEventListener("click", async () => {
      try {
        await resetSession();
        state.scenarioTurn = 0;
        loadScenarioPrompt();
        renderScenarioDetail();
      } catch (error) {
        showError(error.message);
      }
    });
    elements.viewTranscript.addEventListener("click", viewTranscript);
    elements.downloadTranscript.addEventListener("click", () => {
      if (state.session) {
        window.location.assign(`/api/session/${state.session.session_id}/transcript/download`);
      }
    });
    elements.copyTranscriptId.addEventListener("click", copyTranscriptId);
  }

  async function init() {
    try {
      const [meta, scenarios] = await Promise.all([
        request("/api/meta"),
        request("/api/demo-scenarios"),
      ]);
      state.meta = meta;
      state.scenarios = scenarios.scenarios || [];
      renderMetadata();
      renderRegistry();
      setupScenarioFilter();
      renderScenarioList();
      renderScenarioDetail();
      await createSession({ clear: false });
      bindEvents();
    } catch (error) {
      showError(`Không thể khởi tạo giao diện cục bộ: ${error.message}`);
      setStatus("Lỗi khởi tạo", "error");
    }
  }

  init();
})();
