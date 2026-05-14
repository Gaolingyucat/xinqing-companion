/* 呼吸练习脚本：控制呼吸节奏动画、倒计时与开始暂停状态。 */

(function () {
  const wrap = document.getElementById("breathWrap");
  const circle = document.getElementById("breathCircle");
  const textNode = document.getElementById("breathText");
  const countdownNode = document.getElementById("breathCountdown");
  const startBtn = document.getElementById("breathStartBtn");
  const pauseBtn = document.getElementById("breathPauseBtn");
  const finishNode = document.getElementById("breathFinishText");

  if (!wrap || !circle || !textNode || !countdownNode || !startBtn || !pauseBtn || !finishNode) {
    return;
  }

  const totalSeconds = parseInt(wrap.dataset.duration || "60", 10);
  let remaining = totalSeconds;
  let phaseIndex = 0;
  let phaseRemaining = 4;
  let timer = null;
  let isRunning = false;

  const phases = [
    { label: "吸气 4 秒", duration: 4, className: "is-inhale" },
    { label: "停一下", duration: 2, className: "is-hold" },
    { label: "呼气 6 秒", duration: 6, className: "is-exhale" },
  ];

  const resetPhase = (index) => {
    phaseIndex = index;
    phaseRemaining = phases[phaseIndex].duration;
    circle.classList.remove("is-inhale", "is-hold", "is-exhale");
    circle.classList.add(phases[phaseIndex].className);
    textNode.textContent = phases[phaseIndex].label;
  };

  const updateCountdown = () => {
    countdownNode.textContent = `剩余 ${remaining} 秒`;
  };

  const finish = () => {
    clearInterval(timer);
    timer = null;
    isRunning = false;
    textNode.textContent = "完成一次放松练习";
    circle.classList.remove("is-inhale", "is-hold", "is-exhale");
    finishNode.hidden = false;
  };

  const tick = () => {
    if (remaining <= 0) {
      finish();
      return;
    }

    remaining -= 1;
    phaseRemaining -= 1;

    if (phaseRemaining <= 0) {
      resetPhase((phaseIndex + 1) % phases.length);
    }

    updateCountdown();

    if (remaining <= 0) {
      finish();
    }
  };

  const start = () => {
    if (isRunning) {
      return;
    }

    if (remaining <= 0) {
      remaining = totalSeconds;
      resetPhase(0);
      updateCountdown();
      finishNode.hidden = true;
    }

    if (!phases[phaseIndex]) {
      resetPhase(0);
    }

    if (!textNode.textContent || textNode.textContent === "准备开始") {
      resetPhase(0);
    }

    isRunning = true;
    timer = setInterval(tick, 1000);
  };

  const pause = () => {
    if (!isRunning) {
      return;
    }
    clearInterval(timer);
    timer = null;
    isRunning = false;
  };

  updateCountdown();
  startBtn.addEventListener("click", start);
  pauseBtn.addEventListener("click", pause);
})();
