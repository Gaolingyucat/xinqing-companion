/* 语音倾诉脚本：处理录音、播放和语音心情分析展示。 */

(function () {
  const startBtn = document.getElementById("voiceStartBtn");
  const stopBtn = document.getElementById("voiceStopBtn");
  const playBtn = document.getElementById("voicePlayBtn");
  const player = document.getElementById("voicePlayer");
  const status = document.getElementById("voiceStatusText");
  const resultCard = document.getElementById("voiceResultCard");
  const durationText = document.getElementById("voiceDurationText");
  const emotionText = document.getElementById("voiceEmotionText");
  const riskText = document.getElementById("voiceRiskText");
  const suggestionText = document.getElementById("voiceSuggestionText");
  const companionText = document.getElementById("voiceCompanionText");
  const replySourceText = document.getElementById("voiceReplySourceText");
  const analyzeSourceText = document.getElementById("voiceAnalyzeSourceText");
  const confidenceText = document.getElementById("voiceConfidenceText");
  const llmEmotionText = document.getElementById("voiceLlmEmotionText");
  const llmIntentText = document.getElementById("voiceLlmIntentText");
  const llmReasonText = document.getElementById("voiceLlmReasonText");

  if (!startBtn || !stopBtn || !playBtn || !player || !status || !resultCard) {
    return;
  }

  let recorder = null;
  let mediaStream = null;
  let startedAt = 0;
  let recordedBlob = null;

  const updateResult = (data, fallbackDuration) => {
    resultCard.hidden = false;
    const backendDuration = data.features && typeof data.features.duration === "number"
      ? data.features.duration
      : fallbackDuration;
    durationText.textContent = `${Number(backendDuration || 0).toFixed(1)} 秒`;
    emotionText.textContent = data.emotion_cn || "平稳";
    riskText.textContent = `风险等级：${data.risk_level || "低风险"}`;
    suggestionText.textContent = data.suggestion || "你已经把情绪说出来了，先给自己一点空间。";
    if (companionText) {
      companionText.textContent = data.reply || "这段语音已经记录好了。如果你愿意，也可以补充一句现在最明显的感受。";
    }
    if (replySourceText) {
      replySourceText.textContent = data.reply_source || "本地模板";
    }
    if (analyzeSourceText) {
      analyzeSourceText.textContent = data.source || "audio_rule_engine";
    }
    if (confidenceText) {
      const conf = typeof data.confidence === "number" ? `${(data.confidence * 100).toFixed(1)}%` : "-";
      confidenceText.textContent = conf;
    }
    if (llmEmotionText) {
      llmEmotionText.textContent = data.llm_emotion || data.emotion_cn || "中性";
    }
    if (llmIntentText) {
      llmIntentText.textContent = data.llm_intent || "普通聊天";
    }
    if (llmReasonText) {
      llmReasonText.textContent = data.llm_reason || "结合语音参考结果生成陪伴回复。";
    }
  };

  const localEstimate = (duration) => {
    if (duration >= 25) {
      return { emotion_cn: "疲惫", risk_level: "中风险", suggestion: "今天可能有点累了，先让身体慢一点，等会再处理最急的一件事。" };
    }
    if (duration >= 12) {
      return { emotion_cn: "焦虑", risk_level: "中风险", suggestion: "听起来你有些紧绷，先放慢语速，给自己一点点缓冲时间。" };
    }
    return { emotion_cn: "平稳", risk_level: "低风险", suggestion: "语音状态比较平稳，继续按自己的节奏表达就好。" };
  };

  const analyzeAudio = async (blob, durationSec) => {
    const form = new FormData();
    const ext = blob.type.includes("wav") ? "wav" : "webm";
    form.append("audio_blob", blob, `voice_note.${ext}`);

    try {
      const resp = await fetch("/api/app/voice_analyze", {
        method: "POST",
        body: form,
      });
      const payload = await resp.json();
      if (!resp.ok || !payload.ok) {
        throw new Error("刚刚没有成功，再试一次吧。");
      }
      updateResult(payload.result || {}, durationSec);
      status.textContent = "语音状态：已分析";
    } catch (error) {
      const fallback = localEstimate(durationSec);
      updateResult(
        {
          ...fallback,
          reply: `听起来你刚刚的状态有点${fallback.emotion_cn}，不过声音只能作为参考。你愿意补充一句，现在最明显的感受是什么吗？`,
          reply_source: "本地模板",
          source: "audio_rule_engine",
          llm_emotion: fallback.emotion_cn,
          llm_intent: "普通聊天",
          llm_reason: "语音分析暂时不可用，已使用本地陪伴模板。",
        },
        durationSec
      );
      status.textContent = "语音状态：已记录";
    }
  };

  startBtn.addEventListener("click", async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      status.textContent = "当前浏览器不支持录音，可尝试更换浏览器。";
      return;
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorder = new MediaRecorder(mediaStream);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        recordedBlob = new Blob(chunks, { type: chunks[0]?.type || "audio/webm" });
        player.src = URL.createObjectURL(recordedBlob);
        player.hidden = false;

        const durationSec = Math.max((Date.now() - startedAt) / 1000, 1);
        await analyzeAudio(recordedBlob, durationSec);

        if (mediaStream) {
          mediaStream.getTracks().forEach((t) => t.stop());
        }
      };

      recorder.start();
      startedAt = Date.now();
      status.textContent = "语音状态：录音中...";
    } catch (error) {
      status.textContent = "麦克风暂时没有打开成功，请检查权限后再试一次。";
    }
  });

  stopBtn.addEventListener("click", () => {
    if (recorder && recorder.state === "recording") {
      recorder.stop();
      status.textContent = "语音状态：处理中...";
    }
  });

  playBtn.addEventListener("click", () => {
    if (!recordedBlob) {
      status.textContent = "请先录一段语音。";
      return;
    }
    player.play();
  });
})();
