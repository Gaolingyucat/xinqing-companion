/* 多对话脚本：在 localStorage 中管理聊天会话并跳转到指定 sid。 */

(function () {
  const titleInput = document.getElementById("sessionTitleInput");
  const createBtn = document.getElementById("sessionCreateBtn");
  const list = document.getElementById("sessionList");

  if (!titleInput || !createBtn || !list || !window.XQApp) {
    return;
  }

  const presetSeeds = ["学习压力", "人际关系", "睡前倾诉"];

  const ensurePresetSessions = () => {
    const sessions = window.XQApp.getSessions();
    const titles = sessions.map((s) => s.title);
    presetSeeds.forEach((seed) => {
      if (!titles.includes(seed)) {
        window.XQApp.addSession(seed);
      }
    });
  };

  const render = () => {
    const sessions = window.XQApp.getSessions();
    list.innerHTML = "";
    sessions.forEach((session) => {
      const link = document.createElement("a");
      link.className = "session-link";
      link.href = `/app/chat?sid=${encodeURIComponent(session.id)}`;
      link.textContent = session.title || "未命名对话";
      list.appendChild(link);
    });
  };

  createBtn.addEventListener("click", () => {
    const title = titleInput.value.trim() || "新对话";
    const session = window.XQApp.addSession(title);
    titleInput.value = "";
    render();
    window.location.href = `/app/chat?sid=${encodeURIComponent(session.id)}`;
  });

  ensurePresetSessions();
  render();
})();
