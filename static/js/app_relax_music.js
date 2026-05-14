/* 放松音乐脚本：复制搜索词与“我听完了”记录反馈。 */

(function () {
  const wrap = document.getElementById("musicList");
  const feedback = document.getElementById("musicActionFeedback");

  if (!wrap || !feedback) {
    return;
  }

  Array.from(wrap.querySelectorAll(".music-item")).forEach((card, index) => {
    card.style.setProperty("--card-delay", `${index * 0.08}s`);
    card.classList.add("is-animated");
  });

  const setFeedback = (text) => {
    feedback.textContent = text;
  };

  const copyKeyword = async (keyword) => {
    if (!keyword) {
      return false;
    }
    try {
      await navigator.clipboard.writeText(keyword);
      return true;
    } catch (error) {
      return false;
    }
  };

  const markDone = async (title, keyword) => {
    try {
      const resp = await fetch("/api/app/relax/music_done", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title, keyword }),
      });
      const payload = await resp.json();
      return resp.ok && payload.ok;
    } catch (error) {
      return false;
    }
  };

  wrap.addEventListener("click", async (event) => {
    const item = event.target.closest(".music-item");
    if (!item) {
      return;
    }

    const title = item.dataset.title || "放松音乐";
    const keyword = item.dataset.keyword || "放松音乐";

    if (event.target.classList.contains("music-copy-btn")) {
      const ok = await copyKeyword(keyword);
      if (ok) {
        setFeedback(`已复制搜索词：${keyword}`);
      } else {
        setFeedback("复制没有成功，请手动长按复制关键词。");
      }
    }

    if (event.target.classList.contains("music-done-btn")) {
      const ok = await markDone(title, keyword);
      if (ok) {
        setFeedback(`已记录这次放松：${title}`);
      } else {
        setFeedback("这次记录没有成功，再点一次试试。");
      }
    }
  });
})();
