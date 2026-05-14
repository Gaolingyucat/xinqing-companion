/* 首次使用脚本：保存昵称与陪伴偏好到 localStorage。 */

(function () {
  const nicknameInput = document.getElementById("onboardNickname");
  const optionsWrap = document.getElementById("onboardOptions");
  const submitBtn = document.getElementById("onboardSubmitBtn");

  if (!nicknameInput || !optionsWrap || !submitBtn || !window.XQApp) {
    return;
  }

  const profile = window.XQApp.readProfile();
  let selectedStyle = profile.style || "像朋友一样";
  nicknameInput.value = profile.nickname || "";

  const optionButtons = Array.from(optionsWrap.querySelectorAll(".onboard-option"));

  const syncOptionActive = () => {
    optionButtons.forEach((btn) => {
      const style = btn.dataset.style;
      btn.classList.toggle("is-active", style === selectedStyle);
    });
  };

  optionButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedStyle = btn.dataset.style || selectedStyle;
      syncOptionActive();
    });
  });

  submitBtn.addEventListener("click", () => {
    const nickname = nicknameInput.value.trim() || "心晴用户";
    window.XQApp.saveProfile({ nickname, style: selectedStyle, onboarded: true });
    window.location.href = "/app";
  });

  syncOptionActive();
})();
