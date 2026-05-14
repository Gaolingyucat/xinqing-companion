/* 烦恼泡泡脚本：使用可持续追加的“泡泡池”模式，支持漂浮、点击消散与一键清空。 */

(function () {
  const input = document.getElementById("bubbleInput");
  const addBtn = document.getElementById("bubbleAddBtn");
  const clearBtn = document.getElementById("bubbleClearBtn");
  const board = document.getElementById("bubbleBoard");
  const hint = document.getElementById("bubbleHintText");
  const inputHint = document.getElementById("bubbleInputHint");

  if (!input || !addBtn || !clearBtn || !board || !hint || !inputHint) {
    return;
  }

  let bubbleCounter = 0;
  const clearedSoftLines = [
    "这些烦恼先交给泡泡带走一会儿。",
    "你不用一次把所有事都扛住。",
    "慢一点，也没关系。",
  ];

  const randomRange = (min, max) => min + Math.random() * (max - min);

  const readBubbles = () => Array.from(board.querySelectorAll(".worry-bubble:not(.is-pop)"));

  const setHint = (text, fadeIn = false) => {
    hint.textContent = text;
    if (fadeIn) {
      hint.classList.remove("is-visible");
      requestAnimationFrame(() => hint.classList.add("is-visible"));
    }
  };

  const setInputHint = (text) => {
    inputHint.textContent = text;
    inputHint.classList.remove("is-highlight");
    requestAnimationFrame(() => inputHint.classList.add("is-highlight"));
  };

  const buildClearedFeedback = () => {
    const extra = clearedSoftLines[Math.floor(Math.random() * clearedSoftLines.length)];
    return `不一定马上解决，但已经轻一点了。${extra}`;
  };

  const estimateBubbleSize = (text) => {
    const len = String(text || "").length;
    const size = 74 + Math.min(40, len * 4);
    return Math.max(74, Math.min(size, 122));
  };

  const adjustBoardHeight = () => {
    const count = readBubbles().length;
    const height = Math.min(560, Math.max(320, 320 + Math.floor(count / 5) * 56));
    board.style.height = `${height}px`;
  };

  const getPlacedMeta = () => {
    return readBubbles().map((node) => ({
      x: Number(node.dataset.x || 0),
      y: Number(node.dataset.y || 0),
      size: Number(node.dataset.size || 86),
    }));
  };

  const findPosition = (size) => {
    const boardWidth = Math.max(board.clientWidth, 300);
    const boardHeight = Math.max(board.clientHeight, 320);
    const padding = 8;

    const existing = getPlacedMeta();

    const minX = padding;
    const maxX = Math.max(minX + 1, boardWidth - size - padding);
    const minY = padding;
    const maxY = Math.max(minY + 1, boardHeight - size - padding);

    for (let i = 0; i < 36; i += 1) {
      const x = randomRange(minX, maxX);
      const y = randomRange(minY, maxY);

      const overlap = existing.some((item) => {
        const cx = x + size / 2;
        const cy = y + size / 2;
        const ox = item.x + item.size / 2;
        const oy = item.y + item.size / 2;
        const dist = Math.hypot(cx - ox, cy - oy);
        const minDist = (size + item.size) * 0.46;
        return dist < minDist;
      });

      if (!overlap) {
        return { x, y };
      }
    }

    return {
      x: randomRange(minX, maxX),
      y: randomRange(minY, maxY),
    };
  };

  const createBubble = (text) => {
    const bubble = document.createElement("button");
    bubble.type = "button";
    bubble.className = "worry-bubble";

    const size = estimateBubbleSize(text);
    const position = findPosition(size);

    bubbleCounter += 1;
    bubble.dataset.id = String(bubbleCounter);
    bubble.dataset.size = String(size);
    bubble.dataset.x = String(position.x);
    bubble.dataset.y = String(position.y);

    bubble.style.width = `${size}px`;
    bubble.style.height = `${size}px`;
    bubble.style.left = `${position.x}px`;
    bubble.style.top = `${position.y}px`;
    bubble.style.setProperty("--float-x", `${randomRange(-7, 7).toFixed(1)}px`);
    bubble.style.setProperty("--float-y", `${randomRange(-10, -3).toFixed(1)}px`);
    bubble.style.setProperty("--float-duration", `${randomRange(6.4, 9.2).toFixed(2)}s`);
    bubble.style.setProperty("--float-delay", `${randomRange(0, 1.4).toFixed(2)}s`);

    bubble.innerHTML = `<span>${text}</span>`;

    bubble.addEventListener("click", () => {
      if (bubble.classList.contains("is-pop")) {
        return;
      }
      bubble.classList.add("is-poke");
      setTimeout(() => {
        bubble.classList.add("is-pop");
      }, 90);

      setTimeout(() => {
        bubble.remove();
        adjustBoardHeight();
        if (readBubbles().length === 0) {
          setHint(buildClearedFeedback(), true);
        }
      }, 520);
    });

    board.appendChild(bubble);
    adjustBoardHeight();
  };

  const addBubbleFromInput = () => {
    const content = input.value.trim();
    if (!content) {
      setInputHint("先写下一件现在最想放下的事吧。");
      input.focus();
      return;
    }

    createBubble(content);
    input.value = "";
    setHint("点一下泡泡，让它慢慢飘走。", false);
    setInputHint("新的烦恼已经放进泡泡池了。");
  };

  addBtn.addEventListener("click", addBubbleFromInput);

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addBubbleFromInput();
    }
  });

  clearBtn.addEventListener("click", () => {
    readBubbles().forEach((bubble) => bubble.remove());
    adjustBoardHeight();
    setHint("泡泡池已清空，你可以随时再放一个新的烦恼。", true);
    setInputHint("已清空全部泡泡。");
  });

  adjustBoardHeight();
})();
