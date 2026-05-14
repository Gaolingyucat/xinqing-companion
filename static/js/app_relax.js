/* 放松空间脚本：处理“一分钟整理”页面的本地引导交互。 */

(function () {
  const input = document.getElementById("focusInput");
  const btn = document.getElementById("focusGenerateBtn");
  const result = document.getElementById("focusResult");
  const echo = document.getElementById("focusEchoText");

  if (!input || !btn || !result || !echo) {
    return;
  }

  btn.addEventListener("click", () => {
    const content = input.value.trim();
    if (!content) {
      input.focus();
      return;
    }

    echo.textContent = `你刚刚写的是：${content}。先不用一次扛完，我们先把第一步做出来。`;
    result.hidden = false;
  });
})();
