/* App 通用脚本：管理 onboarding、用户偏好与会话本地存储。 */

(function () {
  const PROFILE_KEY = "xinqing_profile";
  const ONBOARD_KEY = "xinqing_onboarded";
  const SESSIONS_KEY = "xinqing_sessions";

  const defaultProfile = {
    nickname: "心晴用户",
    style: "像朋友一样",
    onboarded: false,
  };

  const safeParse = (raw, fallback) => {
    try {
      return JSON.parse(raw);
    } catch (error) {
      return fallback;
    }
  };

  const readProfile = () => {
    const profile = safeParse(localStorage.getItem(PROFILE_KEY), {});
    const onboarded = localStorage.getItem(ONBOARD_KEY) === "1";
    return {
      ...defaultProfile,
      ...profile,
      onboarded,
    };
  };

  const saveProfile = (profile) => {
    const next = {
      nickname: (profile.nickname || defaultProfile.nickname).trim() || defaultProfile.nickname,
      style: profile.style || defaultProfile.style,
    };
    localStorage.setItem(PROFILE_KEY, JSON.stringify(next));
    if (profile.onboarded) {
      localStorage.setItem(ONBOARD_KEY, "1");
    }
    return next;
  };

  const ensureDefaultSession = () => {
    const sessions = safeParse(localStorage.getItem(SESSIONS_KEY), []);
    if (!Array.isArray(sessions) || sessions.length === 0) {
      const seed = [{ id: "default", title: "默认对话", created_at: Date.now() }];
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(seed));
      return seed;
    }
    return sessions;
  };

  const getSessions = () => ensureDefaultSession();

  const addSession = (title) => {
    const sessions = ensureDefaultSession();
    const newSession = {
      id: `sid_${Date.now()}`,
      title: title.trim() || "新对话",
      created_at: Date.now(),
    };
    sessions.unshift(newSession);
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    return newSession;
  };

  const isOnboarded = () => localStorage.getItem(ONBOARD_KEY) === "1";

  window.XQApp = {
    PROFILE_KEY,
    ONBOARD_KEY,
    SESSIONS_KEY,
    readProfile,
    saveProfile,
    isOnboarded,
    getSessions,
    addSession,
  };
})();
