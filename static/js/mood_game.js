/* 情绪星球脚本：选择心情并生成天气文案，可写入一条放松记录。 */

(function () {
  const chipGrid = document.getElementById("moodChipGrid");
  const chips = chipGrid ? Array.from(chipGrid.querySelectorAll(".mood-chip")) : [];
  const planet = document.getElementById("moodPlanet");
  const hint = document.getElementById("moodPlanetHint");
  const generateBtn = document.getElementById("moodGenerateBtn");
  const resultBox = document.getElementById("moodGameResult");
  const weatherText = document.getElementById("moodWeatherText");
  const lineText = document.getElementById("moodLineText");

  if (!chips.length || !planet || !hint || !generateBtn || !resultBox || !weatherText || !lineText) {
    return;
  }

  const moodMap = {
    "轻松": {
      weather: "晴",
      planet: "🌞",
      line: "今天这颗星球比较透亮，继续按自己的节奏走就很好。",
    },
    "有点累": {
      weather: "多云",
      planet: "☁️",
      line: "云有点厚，但还在可承受范围。先把最小的一步做掉。",
    },
    "心里闷": {
      weather: "小雨",
      planet: "🌧",
      line: "今天像小雨天，慢一点没关系。先照顾好呼吸和身体。",
    },
    "快撑不住": {
      weather: "暴雨预警",
      planet: "⛈",
      line: "这会儿风雨有点大。先确认自己安全，再尽快联系可信任的人。",
    },
  };

  let selectedMood = "";

  const updateSelection = (mood) => {
    selectedMood = mood;
    chips.forEach((chip) => {
      chip.classList.toggle("is-active", chip.dataset.mood === mood);
    });
    const info = moodMap[mood];
    if (info) {
      planet.textContent = info.planet;
      planet.classList.remove("is-weather");
      requestAnimationFrame(() => planet.classList.add("is-weather"));
      hint.textContent = `已放入：${mood}`;
    }
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      updateSelection(chip.dataset.mood || "");
    });
  });

  const saveMoodRecord = async (mood, weather, line) => {
    try {
      await fetch("/api/app/relax/mood_game", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ mood, weather, note: line }),
      });
    } catch (error) {
      // 失败时不打断前端体验。
    }
  };

  generateBtn.addEventListener("click", async () => {
    if (!selectedMood) {
      hint.textContent = "先点一个心情，再生成天气。";
      return;
    }

    const info = moodMap[selectedMood];
    if (!info) {
      return;
    }

    weatherText.textContent = `今日心情天气：${info.weather}`;
    lineText.textContent = info.line;
    resultBox.hidden = false;
    resultBox.classList.remove("is-visible");
    requestAnimationFrame(() => resultBox.classList.add("is-visible"));

    await saveMoodRecord(selectedMood, info.weather, info.line);
  });
})();
