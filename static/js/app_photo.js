/* 自拍心情脚本：上传图片并展示表情心情记录。 */

(function () {
  const input = document.getElementById("photoInput");
  const analyzeBtn = document.getElementById("photoAnalyzeBtn");
  const status = document.getElementById("photoStatusText");
  const resultCard = document.getElementById("photoResultCard");
  const preview = document.getElementById("photoPreviewImage");
  const emotionText = document.getElementById("photoEmotionText");
  const confidenceText = document.getElementById("photoConfidenceText");
  const riskText = document.getElementById("photoRiskText");
  const suggestionText = document.getElementById("photoSuggestionText");
  const companionText = document.getElementById("photoCompanionText");
  const replySourceText = document.getElementById("photoReplySourceText");
  const imageSourceText = document.getElementById("photoImageSourceText");
  const llmEmotionText = document.getElementById("photoLlmEmotionText");
  const llmIntentText = document.getElementById("photoLlmIntentText");
  const llmReasonText = document.getElementById("photoLlmReasonText");

  if (!input || !analyzeBtn || !status || !resultCard || !preview) {
    return;
  }

  const normalizeImageSource = (source) => {
    const raw = String(source || "").toLowerCase();
    if (raw.includes("remote")) {
      return "deepface_remote";
    }
    if (raw.includes("local")) {
      return "deepface_local";
    }
    return source || "未知";
  };

  const setResult = (result) => {
    resultCard.hidden = false;
    emotionText.textContent = result.emotion_cn || "中性";
    const conf = typeof result.confidence === "number" ? `${(result.confidence * 100).toFixed(1)}%` : "-";
    confidenceText.textContent = conf;
    riskText.textContent = `风险等级：${result.risk_level || "低风险"}`;
    suggestionText.textContent = result.suggestion || "你已经完成一次表情心情记录。";
    if (companionText) {
      companionText.textContent = result.reply || "这张照片已经记录好了，如果你愿意，也可以再说说此刻的心情。";
    }
    if (replySourceText) {
      replySourceText.textContent = result.reply_source || "本地模板";
    }
    if (imageSourceText) {
      imageSourceText.textContent = normalizeImageSource(result.source);
    }
    if (llmEmotionText) {
      llmEmotionText.textContent = result.llm_emotion || result.emotion_cn || "中性";
    }
    if (llmIntentText) {
      llmIntentText.textContent = result.llm_intent || "普通聊天";
    }
    if (llmReasonText) {
      llmReasonText.textContent = result.llm_reason || "结合图像参考结果生成陪伴回复。";
    }
    status.textContent = result.warning ? "图片状态：分析完成（已切换为本地模板回复）" : "图片状态：分析完成";
  };

  analyzeBtn.addEventListener("click", async () => {
    const file = input.files && input.files[0];
    if (!file) {
      status.textContent = "请先选择一张图片。";
      return;
    }

    preview.src = URL.createObjectURL(file);
    preview.hidden = false;

    const form = new FormData();
    form.append("image_file", file);

    status.textContent = "图片状态：分析中...";

    try {
      const resp = await fetch("/api/app/photo_analyze", {
        method: "POST",
        body: form,
      });
      const payload = await resp.json();
      if (!resp.ok || !payload.ok) {
        throw new Error("这次没有识别出来，可以换一张更清楚的照片。");
      }
      setResult(payload.result || {});
    } catch (error) {
      resultCard.hidden = true;
      status.textContent = "这次没有识别出来，可以换一张更清楚的照片。";
    }
  });
})();
