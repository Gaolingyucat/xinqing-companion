/* 语音陪伴脚本：用文本输入完成轻量陪伴互动。 */

(function () {
  const input = document.getElementById("callInput");
  const sendBtn = document.getElementById("callSendBtn");
  const endBtn = document.getElementById("callEndBtn");
  const replyCard = document.getElementById("callReplyCard");
  const replyText = document.getElementById("callReplyText");
  const metaText = document.getElementById("callMetaText");

  if (!input || !sendBtn || !replyCard || !replyText || !metaText || !window.XQApp) {
    return;
  }

  const buildHistory = (message) => [
    { role: "user", content: message },
  ];

  sendBtn.addEventListener("click", async () => {
    const message = input.value.trim();
    if (!message) {
      input.focus();
      return;
    }

    sendBtn.disabled = true;
    sendBtn.textContent = "陪伴中...";

    try {
      const resp = await fetch("/app/chat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_history: buildHistory(message),
        }),
      });

      const payload = await resp.json();
      if (!resp.ok || !payload.ok) {
        throw new Error(payload.error || "发送失败");
      }

      replyCard.hidden = false;
      replyText.textContent = payload.reply || "我在听，我们可以继续慢慢说。";
      metaText.textContent = `本地识别：${payload.local_emotion_cn || "中性"} · 风险：${payload.risk_level || "低风险"} · 来源：${payload.source || "本地模板"}`;
    } catch (error) {
      replyCard.hidden = false;
      replyText.textContent = "现在网络有点慢，不过我还在。你可以先把最难受的一句写下来。";
      metaText.textContent = "来源：本地兜底";
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "发送给陪伴助手";
    }
  });

  endBtn.addEventListener("click", () => {
    window.location.href = "/app";
  });
})();
