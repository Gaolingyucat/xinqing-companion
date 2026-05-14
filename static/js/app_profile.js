/* 我的页面脚本：展示本地昵称和陪伴偏好。 */

(function () {
  if (!window.XQApp) {
    return;
  }
  const profile = window.XQApp.readProfile();

  const nicknameNode = document.getElementById("profileNicknameText");
  const styleNode = document.getElementById("profileStyleText");
  const clearBtn = document.getElementById("clearLocalRecordsBtn");
  const hintNode = document.getElementById("profileDataHint");

  if (nicknameNode) {
    nicknameNode.textContent = profile.nickname || "心晴用户";
  }

  if (styleNode) {
    styleNode.textContent = profile.style || "像朋友一样";
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      const shouldClear = window.confirm("清空后，这些本地记录就看不到了。确定要清空吗？");
      if (!shouldClear) {
        return;
      }

      localStorage.removeItem("xinqing_chat_messages");
      localStorage.removeItem(window.XQApp.SESSIONS_KEY);

      if (hintNode) {
        hintNode.textContent = "本地记录已清空。你可以随时开始新的心情记录。";
      }
    });
  }
})();
