/* 首页脚本：处理 onboarding 跳转、昵称与问候语展示。 */

(function () {
  if (!window.XQApp) {
    return;
  }

  if (!window.XQApp.isOnboarded()) {
    window.location.replace("/app/onboarding");
    return;
  }

  const profile = window.XQApp.readProfile();
  const nicknameNode = document.getElementById("nicknameText");
  const greetingNode = document.getElementById("greetingText");

  if (nicknameNode) {
    nicknameNode.textContent = profile.nickname || "心晴用户";
  }

  if (greetingNode) {
    const hour = new Date().getHours();
    if (hour < 12) {
      greetingNode.textContent = "早上好";
    } else if (hour < 18) {
      greetingNode.textContent = "下午好";
    } else {
      greetingNode.textContent = "晚上好";
    }
  }
})();
