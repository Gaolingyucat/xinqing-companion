/* 录音前端脚本：负责浏览器录音、上传与结果展示交互。 */

(() => {
  const cfg = window.AUDIO_RECORDER_CONFIG || {};
  const uploadUrl = cfg.uploadUrl || "/audio/record";

  const btnStart = document.getElementById("btn-start-record");
  const btnStop = document.getElementById("btn-stop-record");
  const btnReset = document.getElementById("btn-reset-record");
  if (!btnStart || !btnStop || !btnReset) {
    return;
  }

  const statusNode = document.getElementById("record-status");
  const secondsNode = document.getElementById("record-seconds");
  const warningNode = document.getElementById("record-warning");
  const playerNode = document.getElementById("record-player");

  const resultBox = document.getElementById("audio-result-box");
  const emptyNode = document.getElementById("audio-result-empty");
  const resultWarn = document.getElementById("audio-result-warning");

  const resFilename = document.getElementById("res-filename");
  const resEmotion = document.getElementById("res-emotion");
  const resEmotionEn = document.getElementById("res-emotion-en");
  const resConfidence = document.getElementById("res-confidence");
  const resDuration = document.getElementById("res-duration");
  const resEnergy = document.getElementById("res-energy");
  const resZcr = document.getElementById("res-zcr");
  const resVolume = document.getElementById("res-volume");
  const resRiskScore = document.getElementById("res-risk-score");
  const resRiskLevel = document.getElementById("res-risk-level");
  const resSuggestion = document.getElementById("res-suggestion");

  let mediaRecorder = null;
  let mediaStream = null;
  let chunks = [];
  let timerId = null;
  let seconds = 0;

  function setWarning(message) {
    if (!message) {
      warningNode.style.display = "none";
      warningNode.textContent = "";
      return;
    }
    warningNode.style.display = "block";
    warningNode.textContent = message;
  }

  function setStatus(text) {
    statusNode.textContent = text;
  }

  function resetTimer() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    seconds = 0;
    secondsNode.textContent = "0";
  }

  function beginTimer() {
    resetTimer();
    timerId = setInterval(() => {
      seconds += 1;
      secondsNode.textContent = String(seconds);
    }, 1000);
  }

  function setButtons(recording) {
    btnStart.disabled = recording;
    btnStop.disabled = !recording;
    btnReset.disabled = recording;
  }

  function stopStreamTracks() {
    if (!mediaStream) {
      return;
    }
    for (const track of mediaStream.getTracks()) {
      track.stop();
    }
    mediaStream = null;
  }

  function setResult(result) {
    if (!result) {
      return;
    }
    resultBox.style.display = "block";
    emptyNode.style.display = "none";
    resFilename.textContent = result.filename || "";
    resEmotion.textContent = result.emotion_cn || "";
    resEmotionEn.textContent = result.emotion || "";
    resConfidence.textContent = Number(result.confidence || 0).toFixed(2);
    resDuration.textContent = String((result.features && result.features.duration) || 0);
    resEnergy.textContent = String((result.features && result.features.rms_energy) || 0);
    resZcr.textContent = String((result.features && result.features.zero_crossing_rate) || 0);
    resVolume.textContent = String((result.features && result.features.volume_level) || "");
    resRiskScore.textContent = String(result.risk_score || "");
    resRiskLevel.textContent = String(result.risk_level || "");
    resSuggestion.textContent = String(result.suggestion || "");

    if (result.warning) {
      resultWarn.style.display = "block";
      resultWarn.textContent = result.warning;
    } else {
      resultWarn.style.display = "none";
      resultWarn.textContent = "";
    }
  }

  async function uploadBlob(blob) {
    setStatus("正在上传并分析...");
    const ext = blob.type.includes("wav") ? "wav" : "webm";
    const fileName = `record_${Date.now()}.${ext}`;
    const formData = new FormData();
    formData.append("audio_blob", blob, fileName);

    const resp = await fetch(uploadUrl, {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || "录音上传失败");
    }
    setResult(data.result);
    setStatus("分析完成");
  }

  btnStart.addEventListener("click", async () => {
    setWarning("");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === "undefined") {
      setWarning("当前浏览器不支持录音功能，请使用最新版 Chrome 或 Edge。");
      return;
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (_) {
      setWarning("麦克风权限被拒绝，请在浏览器设置中允许麦克风访问。");
      return;
    }

    chunks = [];
    try {
      mediaRecorder = new MediaRecorder(mediaStream);
    } catch (_) {
      stopStreamTracks();
      setWarning("录音初始化失败，请检查浏览器录音能力。");
      return;
    }

    mediaRecorder.ondataavailable = (evt) => {
      if (evt.data && evt.data.size > 0) {
        chunks.push(evt.data);
      }
    };

    mediaRecorder.onstop = async () => {
      try {
        const mime = mediaRecorder.mimeType || "audio/webm";
        const blob = new Blob(chunks, { type: mime });
        const previewUrl = URL.createObjectURL(blob);
        playerNode.src = previewUrl;
        playerNode.style.display = "block";
        await uploadBlob(blob);
      } catch (err) {
        setStatus("分析失败");
        setWarning(err.message || "录音分析失败，请重试。");
      } finally {
        stopStreamTracks();
        setButtons(false);
      }
    };

    mediaRecorder.start();
    setStatus("正在录音...");
    beginTimer();
    setButtons(true);
  });

  btnStop.addEventListener("click", () => {
    if (!mediaRecorder || mediaRecorder.state !== "recording") {
      return;
    }
    resetTimer();
    mediaRecorder.stop();
    setStatus("录音已停止");
  });

  btnReset.addEventListener("click", () => {
    setWarning("");
    setStatus("未开始");
    resetTimer();
    playerNode.pause();
    playerNode.removeAttribute("src");
    playerNode.style.display = "none";
  });
})();
