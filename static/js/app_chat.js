/* 聊天前端脚本：支持文字/语音/图片输入、会话隔离存储与折叠分析展示。 */

(function () {
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const chatWindow = document.getElementById("chatWindow");
  const sessionTitleNode = document.getElementById("chatSessionTitle");

  const voiceBtn = document.getElementById("chatVoiceBtn");
  const imageBtn = document.getElementById("chatImageBtn");
  const imageInput = document.getElementById("chatImageInput");

  const recorderPanel = document.getElementById("chatRecorderPanel");
  const recorderStatus = document.getElementById("chatRecorderStatus");
  const recorderStartBtn = document.getElementById("chatRecorderStart");
  const recorderStopBtn = document.getElementById("chatRecorderStop");
  const recorderPlayBtn = document.getElementById("chatRecorderPlay");
  const recorderSendBtn = document.getElementById("chatRecorderSend");
  const recorderAudio = document.getElementById("chatRecorderAudio");

  if (!form || !input || !chatWindow || !window.XQApp) {
    return;
  }

  if (!window.XQApp.isOnboarded()) {
    window.location.replace("/app/onboarding");
    return;
  }

  const HISTORY_KEY = "xinqing_chat_messages";
  const params = new URLSearchParams(window.location.search);
  const sid = params.get("sid") || "default";
  const mode = (params.get("mode") || "").trim();

  const ensureSession = () => {
    const sessions = window.XQApp.getSessions();
    const found = sessions.find((s) => s.id === sid);
    if (found) {
      return found;
    }
    const created = {
      id: sid,
      title: sid === "default" ? "默认对话" : "新对话",
      created_at: Date.now(),
    };
    sessions.unshift(created);
    localStorage.setItem(window.XQApp.SESSIONS_KEY, JSON.stringify(sessions));
    return created;
  };

  const session = ensureSession();
  if (sessionTitleNode) {
    sessionTitleNode.textContent = session.title || "AI 陪伴聊天";
  }

  const escapeHtml = (text) =>
    String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const readAllHistory = () => {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || "{}");
    } catch (error) {
      return {};
    }
  };

  const writeAllHistory = (obj) => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(obj));
  };

  const readSessionMessages = () => {
    const all = readAllHistory();
    const rows = all[sid];
    if (Array.isArray(rows)) {
      return rows;
    }
    return [];
  };

  const saveSessionMessages = (rows) => {
    const all = readAllHistory();
    all[sid] = rows.slice(-100);
    writeAllHistory(all);
  };

  const appendBubbleElement = (role, className) => {
    const article = document.createElement("article");
    article.className = `chat-bubble ${role === "user" ? "chat-user" : "chat-ai"} ${className || ""}`.trim();
    chatWindow.appendChild(article);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return article;
  };

  let typingBubbleNode = null;

  const showTypingBubble = () => {
    if (typingBubbleNode) {
      return;
    }
    const bubble = appendBubbleElement("ai", "chat-ai-typing");
    bubble.innerHTML = `
      <div class="typing-dots" aria-label="正在回复">
        <span></span><span></span><span></span>
      </div>
    `;
    typingBubbleNode = bubble;
  };

  const hideTypingBubble = () => {
    if (!typingBubbleNode) {
      return;
    }
    typingBubbleNode.remove();
    typingBubbleNode = null;
  };

  const resolveStatusLabel = (payload) => {
    const source = String(payload.source || "");
    const riskLevel = String(payload.risk_level || "");
    const localEmotion = String(payload.local_emotion_cn || payload.emotion_cn || "");
    const llmIntent = String(payload.llm_intent || "");

    const isSafety =
      source === "crisis" ||
      source === "safety" ||
      source === "本地安全机制" ||
      localEmotion === "危机状态";

    if (isSafety) {
      return { text: "安全提醒", className: "chat-state-safety" };
    }

    if (
      llmIntent === "重点关注" ||
      localEmotion === "高压状态" ||
      riskLevel === "高风险" ||
      riskLevel === "中高风险"
    ) {
      return { text: "状态：重点关注", className: "chat-state-watch" };
    }

    if (riskLevel === "中风险" || ["焦虑", "疲惫", "难过", "愤怒", "有压力"].includes(localEmotion)) {
      return { text: "状态：有压力", className: "chat-state-stress" };
    }

    return { text: "状态：已记录", className: "chat-state-recorded" };
  };

  const normalizeSource = (source) => {
    const raw = String(source || "本地模板");
    if (raw === "crisis" || raw === "safety" || raw === "本地安全机制") {
      return "本地安全机制";
    }
    return raw;
  };

  const buildAnalysisHtml = (payload) => {
    const sourceText = normalizeSource(payload.source);
    const modality = String(payload.input_modality || "").toLowerCase();
    let emotionLabel = "文本情绪";
    if (modality === "voice" || payload.audio_source || payload.audio_duration || payload.audio_confidence) {
      emotionLabel = "语音情绪";
    } else if (modality === "image" || payload.image_source || payload.image_confidence || sourceText.includes("图像")) {
      emotionLabel = "图像情绪";
    } else if (sourceText.includes("语音")) {
      emotionLabel = "语音情绪";
    }

    const rows = [
      [emotionLabel, payload.local_emotion_cn || payload.emotion_cn || "未提供"],
      ...(payload.audio_confidence ? [["置信度", payload.audio_confidence]] : []),
      ...(payload.audio_duration ? [["语音时长", payload.audio_duration]] : []),
      ...(payload.image_confidence ? [["置信度", payload.image_confidence]] : []),
      ["风险等级", payload.risk_level || "未提供"],
      ["AI理解", payload.llm_emotion || "未提供"],
      ["用户意图", payload.llm_intent || "未提供"],
      ["回复来源", sourceText],
      ...(payload.audio_source ? [["语音识别来源", payload.audio_source]] : []),
      ...(payload.image_source ? [["图像识别来源", payload.image_source]] : []),
      ["分析说明", payload.llm_reason || "未提供"],
      ["建议", payload.advice || "未提供"],
    ];

    const warning = String(payload.warning || "").trim();
    const rowsHtml = rows
      .map(([label, value]) => `<li><strong>${escapeHtml(label)}：</strong>${escapeHtml(value)}</li>`)
      .join("");

    const warningHtml = warning
      ? `<p class="chat-analysis-warning">${escapeHtml(warning)}</p>`
      : "";

    return `<ul class="chat-analysis-list">${rowsHtml}</ul>${warningHtml}`;
  };

  const renderUserBubble = (message) => {
    const bubble = appendBubbleElement("user", "chat-user-text");
    bubble.innerHTML = `<p>${escapeHtml(message)}</p>`;
  };

  const renderUserVoiceBubble = (durationSeconds) => {
    const secondsText = Number.isFinite(durationSeconds) && durationSeconds > 0
      ? `（约 ${Math.round(durationSeconds)} 秒）`
      : "";
    const bubble = appendBubbleElement("user", "chat-user-voice");
    bubble.innerHTML = `<p>🎙 用户发送了一段语音${escapeHtml(secondsText)}</p>`;
  };

  const renderUserImageBubble = (previewUrl) => {
    const bubble = appendBubbleElement("user", "chat-user-image-bubble");
    bubble.innerHTML = `<p>📷 用户发送了一张图片</p><img class="chat-user-image" src="${escapeHtml(previewUrl)}" alt="用户上传图片预览">`;
  };

  const renderAiBubble = (payload) => {
    const reply = String(payload.reply || "").trim();
    if (payload.hide_analysis) {
      const bubble = appendBubbleElement("ai", "chat-ai-result");
      bubble.innerHTML = `<p>${escapeHtml(reply)}</p>`;
      return;
    }
    const state = resolveStatusLabel(payload);

    const bubble = appendBubbleElement("ai", "chat-ai-result");
    bubble.innerHTML = `
      <p>${escapeHtml(reply)}</p>
      <div class="chat-state-row">
        <span class="chat-state-badge ${state.className}">${escapeHtml(state.text)}</span>
        <button type="button" class="chat-analysis-toggle" aria-expanded="false">查看分析</button>
      </div>
      <div class="chat-analysis-panel">${buildAnalysisHtml(payload)}</div>
    `;

      const toggle = bubble.querySelector(".chat-analysis-toggle");
    const panel = bubble.querySelector(".chat-analysis-panel");
    if (toggle && panel) {
      toggle.addEventListener("click", () => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
        toggle.textContent = expanded ? "查看分析" : "收起分析";
        panel.classList.toggle("is-open", !expanded);
      });
    }
  };

  const renderErrorBubble = (message) => {
    const bubble = appendBubbleElement("ai", "chat-ai-result");
    bubble.innerHTML = `<p>${escapeHtml(message)}</p>`;
  };

  const getBackendHistory = (rows) =>
    rows
      .slice(-12)
      .map((item) => ({ role: item.role, content: item.content }))
      .filter((item) => item.role && item.content);

  const defaultWelcome = "你好，欢迎来到心晴陪伴。你可以和我聊聊今天的心情，我会陪你一起整理感受。";
  let messages = readSessionMessages();

  const renderSession = () => {
    chatWindow.innerHTML = "";
    if (!messages.length) {
      renderAiBubble({
        reply: defaultWelcome,
        hide_analysis: true,
      });
      messages = [
        {
          role: "ai",
          kind: "text",
          content: defaultWelcome,
          meta: { hide_analysis: true },
        },
      ];
      saveSessionMessages(messages);
      return;
    }

    messages.forEach((msg) => {
      if (msg.role === "user") {
        if (msg.kind === "voice") {
          renderUserVoiceBubble(msg.meta && msg.meta.duration_seconds ? Number(msg.meta.duration_seconds) : 0);
        } else if (msg.kind === "image") {
          if (msg.preview_url) {
            renderUserImageBubble(msg.preview_url);
          } else {
            const bubble = appendBubbleElement("user", "chat-user-image-bubble");
            bubble.innerHTML = "<p>📷 用户发送了一张图片</p>";
          }
        } else {
          renderUserBubble(msg.content);
        }
      } else {
        renderAiBubble({ reply: msg.content, ...(msg.meta || {}) });
      }
    });
  };

  const resolvePhotoSourceLabel = (source) => {
    const text = String(source || "").toLowerCase();
    if (text.includes("remote")) {
      return "deepface_remote";
    }
    if (text.includes("local")) {
      return "deepface_local";
    }
    return source || "unknown";
  };

  const pushAiResult = (replyText, meta) => {
    const payload = {
      reply: replyText,
      local_emotion_cn: meta.local_emotion_cn || meta.emotion_cn || "中性",
      emotion_cn: meta.emotion_cn || meta.local_emotion_cn || "中性",
      risk_level: meta.risk_level || "低风险",
      llm_emotion: meta.llm_emotion || "中性",
      llm_intent: meta.llm_intent || "普通聊天",
      llm_reason: meta.llm_reason || "基于当前输入生成的陪伴反馈。",
      source: meta.source || "本地模板",
      advice: meta.advice || "继续记录也可以帮助你看见情绪变化。",
      warning: meta.warning || "",
      audio_confidence: meta.audio_confidence || "",
      audio_duration: meta.audio_duration || "",
      audio_source: meta.audio_source || "",
      image_confidence: meta.image_confidence || "",
      image_source: meta.image_source || "",
      input_modality: meta.input_modality || "text",
    };

    renderAiBubble(payload);
    messages.push({
      role: "ai",
      kind: "text",
      content: payload.reply,
      meta: {
        local_emotion_cn: payload.local_emotion_cn,
        risk_level: payload.risk_level,
        llm_emotion: payload.llm_emotion,
        llm_intent: payload.llm_intent,
        llm_reason: payload.llm_reason,
        source: payload.source,
        advice: payload.advice,
        warning: payload.warning,
        emotion_cn: payload.emotion_cn,
        audio_confidence: payload.audio_confidence,
        audio_duration: payload.audio_duration,
        audio_source: payload.audio_source,
        image_confidence: payload.image_confidence,
        image_source: payload.image_source,
        input_modality: payload.input_modality,
      },
    });
    saveSessionMessages(messages);
  };

  const sendTextMessage = async (message) => {
    renderUserBubble(message);
    messages.push({ role: "user", kind: "text", content: message, meta: {} });
    saveSessionMessages(messages);
    showTypingBubble();

    try {
      const response = await fetch("/app/chat/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          conversation_history: getBackendHistory(messages),
        }),
      });

      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "发送失败，请稍后重试。");
      }

      pushAiResult(payload.reply || "", {
        local_emotion_cn: payload.local_emotion_cn,
        emotion_cn: payload.emotion_cn,
        risk_level: payload.risk_level,
        llm_emotion: payload.llm_emotion,
        llm_intent: payload.llm_intent,
        llm_reason: payload.llm_reason,
        source: payload.source,
        advice: payload.advice,
        warning: payload.warning,
      });
    } catch (error) {
      renderErrorBubble(error.message || "当前无法处理消息，请稍后再试。");
    } finally {
      hideTypingBubble();
    }
  };

  let mediaRecorder = null;
  let recordChunks = [];
  let recordedBlob = null;
  let recordedDurationSeconds = 0;
  let recorderStream = null;
  let recordStartAt = 0;

  const setRecorderStatus = (text) => {
    if (recorderStatus) {
      recorderStatus.textContent = text;
    }
  };

  const toggleRecorderPanel = () => {
    if (!recorderPanel) {
      return;
    }
    recorderPanel.hidden = !recorderPanel.hidden;
  };

  const startRecord = async () => {
    if (!window.MediaRecorder || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setRecorderStatus("当前浏览器不支持录音，可以先使用文字倾诉。");
      return;
    }

    try {
      recorderStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(recorderStream);
      recordChunks = [];
      recordedBlob = null;
      recordStartAt = Date.now();

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (!recordChunks.length) {
          setRecorderStatus("没有录到声音，请再试一次。");
          return;
        }
        recordedBlob = new Blob(recordChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        const audioUrl = URL.createObjectURL(recordedBlob);
        if (recorderAudio) {
          recorderAudio.src = audioUrl;
          recorderAudio.hidden = false;
        }
        recordedDurationSeconds = Math.max(1, Math.round((Date.now() - recordStartAt) / 1000));
        setRecorderStatus(`录音完成（约 ${recordedDurationSeconds} 秒），可以播放或发送。`);
      };

      mediaRecorder.start();
      setRecorderStatus("正在录音中... 你可以慢慢说。");
    } catch (error) {
      setRecorderStatus("无法开启麦克风，请检查浏览器权限。");
    }
  };

  const stopRecord = () => {
    if (!mediaRecorder || mediaRecorder.state !== "recording") {
      return;
    }
    mediaRecorder.stop();
    if (recorderStream) {
      recorderStream.getTracks().forEach((track) => track.stop());
    }
  };

  const playRecord = () => {
    if (!recordedBlob || !recorderAudio) {
      setRecorderStatus("还没有可播放的录音。");
      return;
    }
    recorderAudio.currentTime = 0;
    recorderAudio.play().catch(() => {
      setRecorderStatus("播放失败，请再试一次。");
    });
  };

  const sendVoiceRecord = async () => {
    if (!recordedBlob) {
      setRecorderStatus("请先完成录音再发送。");
      return;
    }

    const durationSeconds = recordedDurationSeconds || 1;
    renderUserVoiceBubble(durationSeconds);
    messages.push({
      role: "user",
      kind: "voice",
      content: "[voice]",
      meta: { duration_seconds: durationSeconds },
    });
    saveSessionMessages(messages);
    showTypingBubble();

    const formData = new FormData();
    formData.append("audio_blob", recordedBlob, "chat_voice.webm");
    formData.append("conversation_history", JSON.stringify(getBackendHistory(messages)));

    try {
      const response = await fetch("/api/app/voice_analyze", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error("录音没有保存成功，请重新试一下。");
      }

      const result = payload.result || {};
      const confidence = Number(result.confidence || 0);
      const confidenceText = Number.isFinite(confidence) ? `${(confidence * 100).toFixed(1)}%` : "";
      const audioDurationRaw = result.features && result.features.duration;
      const audioDurationText =
        typeof audioDurationRaw === "number" ? `${audioDurationRaw.toFixed(1)} 秒` : `${durationSeconds} 秒`;

      pushAiResult(result.reply || "这段语音已经记录好了，如果你愿意，也可以再说说现在最明显的感受。", {
        local_emotion_cn: result.emotion_cn || "语音记录",
        emotion_cn: result.emotion_cn || "语音记录",
        risk_level: result.risk_level || "中风险",
        llm_emotion: result.llm_emotion || result.emotion_cn || "中性",
        llm_intent: result.llm_intent || "普通聊天",
        llm_reason: result.llm_reason || "结合语音参考结果生成陪伴回复。",
        source: result.reply_source || "本地模板",
        advice: `${result.suggestion || "先给自己一点缓冲时间。"}（语音结果仅作为心情记录参考）`,
        warning: result.warning || "",
        audio_confidence: confidenceText,
        audio_duration: audioDurationText,
        audio_source: result.source || "audio_rule_engine",
        input_modality: "voice",
      });

      setRecorderStatus("语音已发送，已生成陪伴回复。");
    } catch (error) {
      renderErrorBubble(error.message || "刚刚没有成功，再试一次吧。");
      setRecorderStatus("录音没有保存成功，请重新试一下。");
    } finally {
      hideTypingBubble();
    }
  };

  const sendImageMessage = async (file) => {
    if (!file) {
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    renderUserImageBubble(previewUrl);
    messages.push({
      role: "user",
      kind: "image",
      content: "[image]",
      preview_url: previewUrl,
      meta: {},
    });
    saveSessionMessages(messages);
    showTypingBubble();

    const formData = new FormData();
    formData.append("image_file", file);
    formData.append("conversation_history", JSON.stringify(getBackendHistory(messages)));

    try {
      const response = await fetch("/api/app/photo_analyze", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error("这次没有识别出来，可以换一张更清楚的照片。");
      }

      const result = payload.result || {};
      const confidence = Number(result.confidence || 0);
      const confidenceText = Number.isFinite(confidence) ? `${(confidence * 100).toFixed(1)}%` : "";

      pushAiResult(result.reply || "照片已经记录好了，如果你愿意，也可以说说此刻更真实的感受。", {
        local_emotion_cn: result.emotion_cn || "图像记录",
        emotion_cn: result.emotion_cn || "图像记录",
        risk_level: result.risk_level || "低风险",
        llm_emotion: result.llm_emotion || result.emotion_cn || "中性",
        llm_intent: result.llm_intent || "普通聊天",
        llm_reason: result.llm_reason || "结合图像参考结果生成陪伴回复。",
        source: result.reply_source || "本地模板",
        advice: `${result.suggestion || "如果愿意，可以补一句此刻的真实感受。"}（图像结果仅作为心情记录参考）`,
        warning: result.warning || "",
        image_confidence: confidenceText,
        image_source: resolvePhotoSourceLabel(result.source),
        input_modality: "image",
      });
    } catch (error) {
      renderErrorBubble(error.message || "这次没有识别出来，可以换一张更清楚的照片。");
    } finally {
      hideTypingBubble();
    }
  };

  renderSession();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
      return;
    }
    input.value = "";
    input.focus();
    await sendTextMessage(message);
  });

  if (voiceBtn && recorderPanel) {
    voiceBtn.addEventListener("click", toggleRecorderPanel);
  }

  if (imageBtn && imageInput) {
    imageBtn.addEventListener("click", () => imageInput.click());
    imageInput.addEventListener("change", () => {
      const file = imageInput.files && imageInput.files[0];
      if (!file) {
        return;
      }
      sendImageMessage(file);
      imageInput.value = "";
    });
  }

  if (recorderStartBtn) {
    recorderStartBtn.addEventListener("click", startRecord);
  }

  if (recorderStopBtn) {
    recorderStopBtn.addEventListener("click", stopRecord);
  }

  if (recorderPlayBtn) {
    recorderPlayBtn.addEventListener("click", playRecord);
  }

  if (recorderSendBtn) {
    recorderSendBtn.addEventListener("click", sendVoiceRecord);
  }

  if (mode === "voice" && recorderPanel) {
    recorderPanel.hidden = false;
    setRecorderStatus("你可以直接开始录音，慢慢说就好。");
  }

  if (mode === "photo") {
    if (imageBtn) {
      imageBtn.classList.add("is-active");
    }
    renderErrorBubble("可以先点下方的 📷 选择一张照片，记录现在的状态。");
  }
})();
