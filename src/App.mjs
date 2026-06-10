const API_BASE = "http://127.0.0.1:5001/api";
const SESSION_KEY = "shouyu_current_user_v1";
const LEARNING_FAVORITES_KEY = "shouyu_learning_favorites_v1";

const nowText = () => new Date().toLocaleString("zh-CN", { hour12: false });
const formatSize = (size) => {
  if (!Number.isFinite(size)) return "--";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
};
const formatConfidence = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(2)}%`;
};
const parseJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return {};
  }
};
const getInitialAuthMode = () =>
  typeof window !== "undefined" && window.location.hash === "#register" ? "register" : "login";
const loadSession = () => {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};
const saveSession = (user) => localStorage.setItem(SESSION_KEY, JSON.stringify(user));
const clearSession = () => localStorage.removeItem(SESSION_KEY);
const loadLearningFavorites = () => {
  try {
    const raw = localStorage.getItem(LEARNING_FAVORITES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};
const saveLearningFavorites = (favorites) => localStorage.setItem(LEARNING_FAVORITES_KEY, JSON.stringify(favorites));

const buildUserNavGroups = () => [
  { key: "home", label: "首页", tabs: [{ key: "dashboard", label: "用户首页" }] },
  {
    key: "tools",
    label: "功能使用",
    tabs: [
      { key: "learning", label: "学习手语" },
      { key: "predict", label: "模型识别" },
      { key: "camera", label: "实时录制" },
      { key: "contribute", label: "贡献视频" },
    ],
  },
  { key: "records", label: "我的记录", tabs: [{ key: "my-usage", label: "使用记录" }] },
  { key: "system", label: "系统", tabs: [{ key: "about", label: "账号管理" }] },
];

const buildAdminNavGroups = () => [
  { key: "home", label: "首页", tabs: [{ key: "dashboard", label: "管理首页" }] },
  {
    key: "manage",
    label: "管理功能",
    tabs: [
      { key: "learning", label: "学习手语" },
      { key: "users", label: "用户管理" },
    ],
  },
  {
    key: "records",
    label: "记录查看",
    tabs: [
      { key: "usage", label: "使用日志" },
      { key: "contributions", label: "视频贡献" },
    ],
  },
  { key: "system", label: "系统", tabs: [{ key: "about", label: "系统信息" }] },
];

export const App = {
  data() {
    return {
      currentUser: loadSession(),
      clock: nowText(),
      authMode: getInitialAuthMode(),
      activeTab: "dashboard",
      statusType: "idle",
      statusText: "系统已就绪",
      statusDetail: "请先登录并连接后端服务。",
      serviceStatus: "未连接",
      predictorStatus: "未初始化",
      rawResponse: "{}",
      logs: ["前端已加载。"],
      loginForm: { username: "", password: "", role: "user" },
      registerForm: { username: "", display_name: "", password: "" },
      selectedFile: null,
      fileUrl: "",
      fileMeta: "尚未选择识别视频",
      currentSourceMode: "upload",
      resultText: "等待识别",
      resultConfidence: "--",
      resultSource: "--",
      resultTime: "--",
      isInitializing: false,
      isPredicting: false,
      mediaStream: null,
      mediaRecorder: null,
      recordedChunks: [],
      isRecording: false,
      cameraState: "未开启",
      recordState: "未开始",
      adminUsers: [],
      usageLogs: [],
      myUsageLogs: [],
      contributions: [],
      userForm: { id: null, username: "", password: "", role: "user", display_name: "" },
      contributionForm: { file: null, note: "" },
      contributionMeta: "尚未选择贡献视频",
      contributionSource: "未选择",
      contributionFileUrl: "",
      contributionStream: null,
      contributionRecorder: null,
      contributionChunks: [],
      isContributionRecording: false,
      contributionCameraState: "未开启",
      contributionRecordState: "未开始",
      learningMaterials: [],
      selectedLearningId: "",
      learningVideoList: [],
      currentLearningVideoIndex: 0,
      isLearningRefreshing: false,
      learningSearchKeyword: "",
      learningFavorites: loadLearningFavorites(),
      learningOnlyFavorites: false,
      profileForm: {
        username: "",
        display_name: "",
        current_password: "",
        new_password: "",
        confirm_password: "",
      },
      accountMessage: "待修改",
    };
  },
  computed: {
    isLoggedIn() { return Boolean(this.currentUser); },
    isAdmin() { return this.currentUser?.role === "admin"; },
    navGroups() { if (!this.isLoggedIn) return []; return this.isAdmin ? buildAdminNavGroups() : buildUserNavGroups(); },
    activeNavGroup() { return this.navGroups.find((group) => group.tabs.some((tab) => tab.key === this.activeTab)) || this.navGroups[0] || null; },
    confidenceWidth() { if (this.resultConfidence === "--") return "0%"; const numeric = Number.parseFloat(this.resultConfidence); return Number.isNaN(numeric) ? "0%" : `${Math.max(0, Math.min(100, numeric))}%`; },
    videoPreviewUrl() { return this.fileUrl; },
    filteredLearningMaterials() {
      const keyword = this.learningSearchKeyword.trim();
      return this.learningMaterials.filter((item) => {
        const matchFavorite = !this.learningOnlyFavorites || this.learningFavorites.includes(item.id);
        const matchKeyword = !keyword || item.name.includes(keyword) || item.description.includes(keyword) || String(item.label).includes(keyword);
        return matchFavorite && matchKeyword;
      });
    },
    selectedLearning() { return this.learningMaterials.find((item) => item.id === this.selectedLearningId) || null; },
    currentLearningVideo() { return this.learningVideoList[this.currentLearningVideoIndex] || null; },
    selectedLearningVideoSrc() { return this.currentLearningVideo ? `http://127.0.0.1:5001${this.currentLearningVideo.url}` : ""; },
    favoriteLearningMaterials() { return this.learningMaterials.filter((item) => this.learningFavorites.includes(item.id)); },
    isCurrentLearningFavorite() { return this.selectedLearning ? this.learningFavorites.includes(this.selectedLearning.id) : false; },
    filteredContributions() { if (this.isAdmin) return this.contributions; return this.contributions.filter((item) => item.username === this.currentUser?.username); },
  },
  watch: {
    selectedLearningId() { this.loadLearningVideos(); },
    learningSearchKeyword() { this.ensureSelectedLearningVisible(); },
    learningOnlyFavorites() { this.ensureSelectedLearningVisible(); },
  },
  mounted() { this.clockTimer = window.setInterval(() => { this.clock = nowText(); }, 1000); this.checkService({ notify: false }); this.syncProfileForm(); if (this.currentUser) this.afterLoginSetup(); },
  beforeUnmount() { window.clearInterval(this.clockTimer); this.stopCamera(); this.stopContributionCamera(); if (this.fileUrl) URL.revokeObjectURL(this.fileUrl); if (this.contributionFileUrl) URL.revokeObjectURL(this.contributionFileUrl); },
  methods: {
    addLog(message) { this.logs.unshift(`[${nowText()}] ${message}`); this.logs = this.logs.slice(0, 200); },
    setStatus(type, text, detail) { this.statusType = type; this.statusText = text; this.statusDetail = detail; this.serviceStatus = type === "ok" ? "已连接" : type === "warn" ? "处理中" : type === "error" ? "异常" : "未连接"; },
    authHeaders(extra = {}) { return { "X-User-Name": this.currentUser?.username || "anonymous", "X-User-Role": this.currentUser?.role || "guest", ...extra }; },
    async apiGet(path) { const response = await fetch(`${API_BASE}${path}`, { headers: this.authHeaders() }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "请求失败"); return data; },
    async apiJson(path, method, body) { const response = await fetch(`${API_BASE}${path}`, { method, headers: this.authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify(body) }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "请求失败"); return data; },
    roleLabel(role) { return role === "admin" ? "管理员" : "用户"; },
    actionLabel(action) { const mapping = { login: "登录系统", register: "注册账号", predict_video: "视频识别", contribute_video: "贡献视频" }; return mapping[action] || action || "--"; },
    goAuthPage(mode) { if (typeof window === "undefined") { this.authMode = mode; return; } window.location.hash = mode === "register" ? "#register" : "#login"; window.location.reload(); },
    selectNavGroup(groupKey) { const group = this.navGroups.find((item) => item.key === groupKey); if (!group?.tabs?.length) return; this.activeTab = group.tabs[0].key; },
    switchTab(tab) { this.activeTab = tab; },
    syncProfileForm() {
      this.profileForm = {
        username: this.currentUser?.username || "",
        display_name: this.currentUser?.display_name || "",
        current_password: "",
        new_password: "",
        confirm_password: "",
      };
      this.accountMessage = "待修改";
    },
    ensureSelectedLearningVisible() {
      if (!this.filteredLearningMaterials.length) return;
      const exists = this.filteredLearningMaterials.some((item) => item.id === this.selectedLearningId);
      if (!exists) this.selectedLearningId = this.filteredLearningMaterials[0].id;
    },
    async checkService(options = {}) {
      const { notify = true } = options;
      try {
        const response = await fetch("http://127.0.0.1:5001/api/health");
        const data = await parseJson(response);
        if (!response.ok || !data.success) throw new Error(data.message || "后端服务检查失败");
        this.setStatus("ok", "后端已连接", "后端接口可以正常访问。");
        this.addLog("后端健康检查成功。");
        if (notify && typeof window !== "undefined" && typeof window.alert === "function") {
          const detail = [
            "后端服务检查成功",
            `服务名称：${data.service || "未知"}`,
            `预测器可用：${data.predictor_available ? "是" : "否"}`,
            `预测器已初始化：${data.predictor_initialized ? "是" : "否"}`,
            `导入错误：${data.import_error || "无"}`,
          ].join("\n");
          window.alert(detail);
        }
      } catch (error) {
        const message = error.message || "请先启动后端服务。";
        this.setStatus("error", "后端不可用", message);
        this.addLog(`后端健康检查失败：${message}`);
        if (notify && typeof window !== "undefined" && typeof window.alert === "function") {
          window.alert(`后端服务检查失败\n${message}`);
        }
      }
    },
    async login() { try { const response = await fetch(`${API_BASE}/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(this.loginForm) }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "登录失败"); this.currentUser = data.user; saveSession(this.currentUser); this.syncProfileForm(); this.activeTab = "dashboard"; this.setStatus("ok", "登录成功", `当前身份：${this.roleLabel(this.currentUser.role)}`); this.addLog(`${this.currentUser.username} 已登录，身份为${this.roleLabel(this.currentUser.role)}。`); await this.afterLoginSetup(); } catch (error) { const message = error.message || "请检查账号信息。"; this.setStatus("error", "登录失败", message); this.addLog(`登录失败：${message}`); if (typeof window !== "undefined" && typeof window.alert === "function") window.alert(message); } },
    async registerUser() { try { const response = await fetch(`${API_BASE}/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(this.registerForm) }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "注册失败"); this.setStatus("ok", "注册成功", "已注册普通用户，请返回登录页。"); this.addLog(`新用户已注册：${data.user.username}`); this.loginForm.username = this.registerForm.username; this.loginForm.password = this.registerForm.password; this.loginForm.role = "user"; this.registerForm = { username: "", display_name: "", password: "" }; this.goAuthPage("login"); } catch (error) { this.setStatus("error", "注册失败", error.message || "请检查注册信息。"); this.addLog(`注册失败：${error.message || "未知错误"}`); } },
    async afterLoginSetup() { await this.checkService({ notify: false }); await this.fetchLearningMaterials(); if (this.isAdmin) { await Promise.allSettled([this.fetchUsers(), this.fetchUsageLogs(), this.fetchContributions()]); } else { await Promise.allSettled([this.fetchMyUsageLogs(), this.fetchContributions()]); } },
    logout() { this.currentUser = null; clearSession(); this.syncProfileForm(); this.activeTab = "dashboard"; this.adminUsers = []; this.usageLogs = []; this.myUsageLogs = []; this.contributions = []; this.setStatus("idle", "已退出登录", "如需继续使用，请重新登录。"); this.addLog("用户已退出登录。"); },
    handlePredictFileChange(event) { const [file] = event.target.files || []; this.bindPredictionFile(file, "upload"); },
    bindPredictionFile(file, sourceMode) { if (!file) { this.selectedFile = null; this.fileMeta = "尚未选择识别视频"; if (this.fileUrl) URL.revokeObjectURL(this.fileUrl); this.fileUrl = ""; return; } if (this.fileUrl) URL.revokeObjectURL(this.fileUrl); this.selectedFile = file; this.fileUrl = URL.createObjectURL(file); this.currentSourceMode = sourceMode; this.fileMeta = `文件：${file.name} | 大小：${formatSize(file.size)} | 类型：${file.type || "未知"}`; this.addLog(`已选择识别视频：${file.name}`); },
    async initPredictor() { this.isInitializing = true; this.setStatus("warn", "正在初始化模型", "正在从后端加载预测器。"); try { const data = await this.apiJson("/init-predictor", "POST", { model_type: "cnn_lstm" }); this.rawResponse = JSON.stringify(data, null, 2); this.predictorStatus = data.predictor_impl === "real" ? "真实模型" : data.predictor_impl || "已初始化"; this.setStatus("ok", "模型初始化成功", "预测器已准备就绪。"); this.addLog("预测器初始化成功。"); } catch (error) { this.predictorStatus = "初始化失败"; this.setStatus("error", "模型初始化失败", error.message || "请检查模型文件。"); this.addLog(`模型初始化失败：${error.message || "未知错误"}`); } finally { this.isInitializing = false; } },
    async initAndPredict() { if (this.predictorStatus === "未初始化" || this.predictorStatus === "初始化失败") { await this.initPredictor(); if (this.predictorStatus === "未初始化" || this.predictorStatus === "初始化失败") return; } await this.runPrediction(); },
    async runPrediction() { if (!this.selectedFile) { this.setStatus("warn", "缺少识别视频", "请先上传视频或录制视频。"); return; } this.isPredicting = true; this.resultText = "识别中..."; this.resultConfidence = "--"; this.resultTime = "--"; this.setStatus("warn", "正在识别", "正在向后端上传视频并进行推理。"); try { const formData = new FormData(); formData.append("video", this.selectedFile); const response = await fetch(`${API_BASE}/predict-video`, { method: "POST", headers: this.authHeaders(), body: formData }); const data = await parseJson(response); this.rawResponse = JSON.stringify(data, null, 2); if (!response.ok || !data.success) throw new Error(data.message || "识别失败"); this.resultText = data.result || "未返回结果"; this.resultConfidence = formatConfidence(data.confidence); this.resultSource = this.currentSourceMode === "camera" ? "实时录制" : "本地上传"; this.resultTime = nowText(); this.predictorStatus = data.predictor_impl === "real" ? "真实模型" : data.predictor_impl || this.predictorStatus; this.setStatus("ok", "识别完成", "识别结果已返回。"); this.addLog(`识别完成：${this.resultText}`); await this.fetchMyUsageLogs(); if (this.isAdmin) await this.fetchUsageLogs(); } catch (error) { this.resultText = "识别失败"; this.setStatus("error", "识别失败", error.message || "请稍后重试。"); this.addLog(`识别失败：${error.message || "未知错误"}`); } finally { this.isPredicting = false; } },
    async openCamera() { if (this.mediaStream) return; try { this.mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false }); if (this.$refs.cameraVideo) this.$refs.cameraVideo.srcObject = this.mediaStream; this.cameraState = "已开启"; this.recordState = "未开始"; this.addLog("识别摄像头已开启。"); } catch (error) { this.setStatus("error", "摄像头开启失败", error.message || "请允许浏览器访问摄像头。"); } },
    async toggleRecording() { if (this.isRecording) { this.mediaRecorder?.stop(); return; } if (!this.mediaStream) { await this.openCamera(); if (!this.mediaStream) return; } this.recordedChunks = []; const preferred = MediaRecorder.isTypeSupported("video/webm;codecs=vp8") ? "video/webm;codecs=vp8" : "video/webm"; this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: preferred }); this.mediaRecorder.ondataavailable = (event) => { if (event.data && event.data.size > 0) this.recordedChunks.push(event.data); }; this.mediaRecorder.onstop = () => { if (!this.recordedChunks.length) return; const blob = new Blob(this.recordedChunks, { type: this.mediaRecorder.mimeType || "video/webm" }); const file = new File([blob], `webcam_capture_${Date.now()}.webm`, { type: blob.type }); this.bindPredictionFile(file, "camera"); this.recordState = "录制完成"; this.isRecording = false; this.activeTab = "predict"; this.addLog(`录制完成：${file.name}`); }; this.mediaRecorder.start(); this.isRecording = true; this.recordState = "录制中"; this.addLog("开始录制识别视频。"); },
    stopCamera() { if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") this.mediaRecorder.stop(); if (this.mediaStream) { this.mediaStream.getTracks().forEach((track) => track.stop()); this.mediaStream = null; } this.cameraState = "未开启"; if (!this.isRecording) this.recordState = "未开始"; if (this.$refs.cameraVideo) this.$refs.cameraVideo.srcObject = null; },
    setContributionFile(file, source) { if (this.contributionFileUrl) URL.revokeObjectURL(this.contributionFileUrl); if (!file) { this.contributionForm.file = null; this.contributionFileUrl = ""; this.contributionSource = "未选择"; this.contributionMeta = "尚未选择贡献视频"; return; } this.contributionForm.file = file; this.contributionFileUrl = URL.createObjectURL(file); this.contributionSource = source === "camera" ? "现场录制" : "文件上传"; this.contributionMeta = `文件：${file.name} | 大小：${formatSize(file.size)} | 类型：${file.type || "未知"}`; this.addLog(`已准备贡献视频：${file.name}`); },
    handleContributionFileChange(event) { const [file] = event.target.files || []; this.setContributionFile(file || null, "upload"); },
    async openContributionCamera() { if (this.contributionStream) return; try { this.contributionStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false }); if (this.$refs.contributionCameraVideo) this.$refs.contributionCameraVideo.srcObject = this.contributionStream; this.contributionCameraState = "已开启"; this.contributionRecordState = "未开始"; this.addLog("贡献摄像头已开启。"); } catch (error) { this.setStatus("error", "贡献摄像头开启失败", error.message || "请允许浏览器访问摄像头。"); } },
    async toggleContributionRecording() { if (this.isContributionRecording) { this.contributionRecorder?.stop(); return; } if (!this.contributionStream) { await this.openContributionCamera(); if (!this.contributionStream) return; } this.contributionChunks = []; const preferred = MediaRecorder.isTypeSupported("video/webm;codecs=vp8") ? "video/webm;codecs=vp8" : "video/webm"; this.contributionRecorder = new MediaRecorder(this.contributionStream, { mimeType: preferred }); this.contributionRecorder.ondataavailable = (event) => { if (event.data && event.data.size > 0) this.contributionChunks.push(event.data); }; this.contributionRecorder.onstop = () => { if (!this.contributionChunks.length) return; const blob = new Blob(this.contributionChunks, { type: this.contributionRecorder.mimeType || "video/webm" }); const file = new File([blob], `contribution_${Date.now()}.webm`, { type: blob.type }); this.setContributionFile(file, "camera"); this.contributionRecordState = "录制完成"; this.isContributionRecording = false; this.addLog(`现场录制完成：${file.name}`); }; this.contributionRecorder.start(); this.isContributionRecording = true; this.contributionRecordState = "录制中"; this.addLog("开始现场录制贡献视频。"); },
    stopContributionCamera() { if (this.contributionRecorder && this.contributionRecorder.state !== "inactive") this.contributionRecorder.stop(); if (this.contributionStream) { this.contributionStream.getTracks().forEach((track) => track.stop()); this.contributionStream = null; } this.contributionCameraState = "未开启"; if (!this.isContributionRecording) this.contributionRecordState = "未开始"; if (this.$refs.contributionCameraVideo) this.$refs.contributionCameraVideo.srcObject = null; },
    resetContributionForm() { this.contributionForm = { file: null, note: "" }; this.contributionMeta = "尚未选择贡献视频"; this.contributionSource = "未选择"; if (this.contributionFileUrl) URL.revokeObjectURL(this.contributionFileUrl); this.contributionFileUrl = ""; },
    async submitContribution() { if (!this.contributionForm.file) { this.setStatus("warn", "缺少贡献视频", "请先上传文件或完成现场录制。"); return; } if (!this.contributionForm.note.trim()) { this.setStatus("warn", "缺少手语含义", "请先输入这段手语视频表达的意思。"); return; } try { const formData = new FormData(); formData.append("video", this.contributionForm.file); formData.append("note", this.contributionForm.note.trim()); const response = await fetch(`${API_BASE}/contributions`, { method: "POST", headers: this.authHeaders(), body: formData }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "上传失败"); this.setStatus("ok", "贡献视频上传成功", "视频和手语含义说明已保存。"); this.addLog(`贡献视频上传成功：${data.contribution.file_name}`); this.resetContributionForm(); this.stopContributionCamera(); await this.fetchContributions(); await this.fetchMyUsageLogs(); if (this.isAdmin) await this.fetchUsageLogs(); } catch (error) { this.setStatus("error", "贡献视频上传失败", error.message || "请重试上传。"); } },
    async updateAccount() {
      if (!this.profileForm.current_password) {
        this.setStatus("warn", "缺少当前密码", "请输入当前密码后再保存。");
        this.accountMessage = "请输入当前密码";
        return;
      }
      try {
        const response = await fetch(`${API_BASE}/account`, {
          method: "PUT",
          headers: this.authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({
            username: this.currentUser.username,
            display_name: this.profileForm.display_name.trim(),
            current_password: this.profileForm.current_password,
            new_password: this.profileForm.new_password,
            confirm_password: this.profileForm.confirm_password,
          }),
        });
        const data = await parseJson(response);
        if (!response.ok || !data.success) throw new Error(data.message || "账号更新失败");
        this.currentUser = data.user;
        saveSession(this.currentUser);
        this.syncProfileForm();
        this.setStatus("ok", "账号信息已更新", "用户名、昵称或密码修改已保存。");
        this.accountMessage = "修改成功";
        this.addLog(`账号信息已更新：${this.currentUser.username}`);
        await Promise.allSettled([this.fetchMyUsageLogs(), this.fetchContributions()]);
      } catch (error) {
        const message = error.message || "请稍后重试。";
        this.setStatus("error", "账号更新失败", message);
        this.accountMessage = message.replace(/[。]$/u, "");
      }
    },
    async fetchUsers() { const data = await this.apiGet("/users"); this.adminUsers = data.users || []; },
    editUser(user) { this.userForm = { id: user.id, username: user.username, password: "", role: user.role, display_name: user.display_name || "" }; },
    resetUserForm() { this.userForm = { id: null, username: "", password: "", role: "user", display_name: "" }; },
    async saveUser() { try { if (this.userForm.id) { await this.apiJson(`/users/${this.userForm.id}`, "PUT", this.userForm); this.addLog(`已更新用户：${this.userForm.username}`); } else { await this.apiJson("/users", "POST", this.userForm); this.addLog(`已新增用户：${this.userForm.username}`); } this.resetUserForm(); await this.fetchUsers(); await this.fetchUsageLogs(); } catch (error) { this.setStatus("error", "用户保存失败", error.message || "请检查用户信息。"); } },
    async deleteUser(user) { try { const response = await fetch(`${API_BASE}/users/${user.id}`, { method: "DELETE", headers: this.authHeaders() }); const data = await parseJson(response); if (!response.ok || !data.success) throw new Error(data.message || "删除失败"); this.addLog(`已删除用户：${user.username}`); await this.fetchUsers(); await this.fetchUsageLogs(); } catch (error) { this.setStatus("error", "删除用户失败", error.message || "请重试。"); } },
    async fetchUsageLogs() { const data = await this.apiGet("/usage-logs"); this.usageLogs = data.logs || []; },
    async fetchMyUsageLogs() { if (!this.currentUser) return; const data = await this.apiGet("/my-usage"); this.myUsageLogs = data.logs || []; },
    async fetchContributions() { if (!this.currentUser) return; const data = await this.apiGet("/contributions"); this.contributions = data.contributions || []; },
    async fetchLearningMaterials() {
      const currentId = this.selectedLearningId;
      this.isLearningRefreshing = true;
      try {
        const response = await fetch(`${API_BASE}/learning-materials`);
        const data = await parseJson(response);
        if (!response.ok || !data.success) throw new Error(data.message || "学习素材加载失败");
        this.learningMaterials = data.materials || [];
        const matched = this.learningMaterials.find((item) => item.id === currentId);
        this.selectedLearningId = matched ? matched.id : (this.learningMaterials[0]?.id || "");
        this.ensureSelectedLearningVisible();
        await this.loadLearningVideos(true);
        this.setStatus("ok", "学习素材已刷新", `当前共加载 ${this.learningMaterials.length} 个手语学习类别。`);
        this.addLog(`学习素材刷新完成，共加载 ${this.learningMaterials.length} 个类别`);
      } catch (error) {
        this.addLog(`学习素材加载失败：${error.message || "未知错误"}`);
        this.setStatus("error", "学习素材加载失败", error.message || "请检查后端服务");
      } finally {
        this.isLearningRefreshing = false;
      }
    },
    async loadLearningVideos(resetIndex = true) {
      if (!this.selectedLearningId) {
        this.learningVideoList = [];
        this.currentLearningVideoIndex = 0;
        return;
      }
      try {
        const data = await this.apiGet(`/learning-materials/${encodeURIComponent(this.selectedLearningId)}/videos`);
        const nextList = data.videos || [];
        const currentName = resetIndex ? "" : (this.currentLearningVideo?.name || "");
        this.learningVideoList = nextList;
        const matchedIndex = nextList.findIndex((item) => item.name === currentName);
        this.currentLearningVideoIndex = matchedIndex >= 0 ? matchedIndex : 0;
      } catch (error) {
        this.learningVideoList = [];
        this.currentLearningVideoIndex = 0;
        this.addLog(`学习视频列表加载失败：${error.message || "未知错误"}`);
      }
    },
    toggleLearningFavorite() {
      if (!this.selectedLearning) return;
      const id = this.selectedLearning.id;
      if (this.learningFavorites.includes(id)) {
        this.learningFavorites = this.learningFavorites.filter((item) => item !== id);
        this.setStatus("ok", "已取消收藏", `已将“${this.selectedLearning.name}”移出常学句子。`);
        this.addLog(`取消收藏学习句子：${this.selectedLearning.name}`);
      } else {
        this.learningFavorites = [...this.learningFavorites, id];
        this.setStatus("ok", "已加入收藏", `已将“${this.selectedLearning.name}”加入常学句子。`);
        this.addLog(`收藏学习句子：${this.selectedLearning.name}`);
      }
      saveLearningFavorites(this.learningFavorites);
      this.ensureSelectedLearningVisible();
    },
    pickFavoriteLearning(itemId) {
      this.learningOnlyFavorites = false;
      this.selectedLearningId = itemId;
    },
    goToPreviousLearningVideo() {
      if (!this.learningVideoList.length) return;
      this.currentLearningVideoIndex = (this.currentLearningVideoIndex - 1 + this.learningVideoList.length) % this.learningVideoList.length;
      this.setStatus("ok", "已切换到上一条素材", `当前为“${this.selectedLearning?.name || "当前类别"}”的第 ${this.currentLearningVideoIndex + 1} 条示例视频。`);
    },
    goToNextLearningVideo() {
      if (!this.learningVideoList.length) return;
      this.currentLearningVideoIndex = (this.currentLearningVideoIndex + 1) % this.learningVideoList.length;
      this.setStatus("ok", "已切换到下一条素材", `当前为“${this.selectedLearning?.name || "当前类别"}”的第 ${this.currentLearningVideoIndex + 1} 条示例视频。`);
    },
    async refreshLearningVideo() {
      if (!this.selectedLearning) {
        this.setStatus("warn", "未选择学习素材", "请先选择一个手语类别。");
        return;
      }
      if (this.learningVideoList.length <= 1) {
        this.setStatus("warn", "当前类别仅有一条素材", `“${this.selectedLearning.name}” 暂无其他可随机切换的视频示例。`);
        return;
      }
      this.isLearningRefreshing = true;
      try {
        let nextIndex = this.currentLearningVideoIndex;
        while (nextIndex === this.currentLearningVideoIndex) {
          nextIndex = Math.floor(Math.random() * this.learningVideoList.length);
        }
        this.currentLearningVideoIndex = nextIndex;
        this.setStatus("ok", "学习视频已随机切换", `已为“${this.selectedLearning.name}”随机切换到另一条示例视频。`);
        this.addLog(`学习视频已随机切换：${this.selectedLearning.name} -> ${this.currentLearningVideo?.name || "--"}`);
      } catch (error) {
        this.setStatus("error", "学习视频刷新失败", error.message || "请检查后端服务");
        this.addLog(`学习视频刷新失败：${error.message || "未知错误"}`);
      } finally {
        this.isLearningRefreshing = false;
      }
    },
  },
  template: `
<div class="shell">
  <div class="bg-orb bg-orb-a"></div>
  <div class="bg-orb bg-orb-b"></div>
  <template v-if="!isLoggedIn">
    <section class="auth-stage">
      <span class="auth-side auth-side-left">体验案例五</span>
      <span class="auth-side auth-side-right">{{ authMode === 'login' ? '登录页设计' : '注册页设计' }}</span>
      <span class="auth-index">05</span>
      <div class="panel auth-panel auth-poster">
        <div class="auth-noise"></div>
        <div class="auth-bubble auth-bubble-a"></div>
        <div class="auth-bubble auth-bubble-b"></div>
        <div class="auth-bubble auth-bubble-c"></div>
        <div class="auth-topbar"><span class="auth-brand-mark"></span><strong>Sign Language Recognition System</strong><div class="auth-topnav"></div></div>
        <div class="auth-layout">
          <div class="auth-showcase">
            <span class="eyebrow">{{ authMode === 'login' ? '登录入口' : '注册入口' }}</span>
            <div class="auth-showcase-brand">
              <span class="auth-logo-dot"></span>

            </div>
            <h1>{{ authMode === 'login' ? '手语识别系统使用平台' : '用户注册' }}</h1>
            <h3>{{ authMode === 'login' ? '在线手语识别，视频数据上传识别，数据贡献集' : '完成注册后即可返回登录页进行登录' }}</h3>
            <p>{{ authMode === 'login' ? '管理员可进行用户管理与日志查看，普通用户可完成视频识别、实时录制、学习手语和贡献视频。' : '注册页面仅开放普通用户，管理员账号由系统统一维护。' }}</p>
            <div class="auth-grid auth-grid-poster"><div class="mini-card"><span>管理员默认账号</span><strong>admin / admin123</strong></div><div class="mini-card"><span>用户默认账号</span><strong>user1 / user123</strong></div></div>
          </div>
          <div class="auth-form-card">
            <div class="auth-form-head"><span class="auth-form-kicker">{{ authMode === 'login' ? '欢迎回来' : '创建账号' }}</span><h2>{{ authMode === 'login' ? '进入手语识别平台' : '注册普通用户账号' }}</h2><p>{{ authMode === 'login' ? '输入账号信息后即可进入系统。' : '填写基础信息后即可返回登录。' }}</p></div>
            <div class="actions auth-switch"><button v-if="authMode === 'login'" class="ghost-btn" @click="goAuthPage('register')">注册用户</button><button v-else class="ghost-btn" @click="goAuthPage('login')">返回登录</button></div>
            <div v-if="authMode === 'login'" class="form-grid auth-form-grid"><label class="field"><span>登录角色</span><select v-model="loginForm.role"><option value="user">用户</option><option value="admin">管理员</option></select></label><label class="field auth-field-wide"><span>用户名</span><input v-model="loginForm.username" placeholder="请输入用户名"></label><label class="field auth-field-wide"><span>密码</span><input v-model="loginForm.password" type="password" placeholder="请输入密码"></label></div>
            <div v-else class="form-grid auth-form-grid"><label class="field"><span>用户名</span><input v-model="registerForm.username" placeholder="请输入注册用户名"></label><label class="field"><span>显示名称</span><input v-model="registerForm.display_name" placeholder="请输入显示名称"></label><label class="field auth-field-wide"><span>密码</span><input v-model="registerForm.password" type="password" placeholder="请输入注册密码"></label></div>
            <div class="actions auth-submit"><button v-if="authMode === 'login'" class="primary-btn auth-main-btn" @click="login">登录系统</button><button v-else class="primary-btn auth-main-btn" @click="registerUser">提交注册</button><button class="ghost-btn" @click="checkService">检查后端服务</button></div>
          </div>
        </div>
      </div>
    </section>
  </template>
  <template v-else>
    <header class="hero panel"><div class="hero-copy"><span class="eyebrow">{{ isAdmin ? '管理员面板' : '用户面板' }}</span><h1>手语识别与管理平台</h1><p>当前登录用户：<strong>{{ currentUser.display_name || currentUser.username }}</strong>（{{ roleLabel(currentUser.role) }}）</p></div><div class="hero-stats"><div class="mini-card"><span>当前时间</span><strong>{{ clock }}</strong></div><div class="mini-card"><span>服务状态</span><strong>{{ serviceStatus }}</strong></div><div class="mini-card"><span>模型状态</span><strong>{{ predictorStatus }}</strong></div><div class="mini-card"><span>登录身份</span><strong>{{ roleLabel(currentUser.role) }}</strong></div></div></header>
    <section class="status-bar panel" :class="'status-' + statusType"><div><strong>{{ statusText }}</strong><p>{{ statusDetail }}</p></div><div class="actions slim"><button class="ghost-btn" @click="checkService">检查服务</button><button class="ghost-btn" @click="logout">退出登录</button></div></section>
    <nav class="tabs panel"><div class="tab-group-row"><button v-for="group in navGroups" :key="group.key" class="tab-btn level-one" :class="{ active: activeNavGroup && activeNavGroup.key === group.key }" @click="selectNavGroup(group.key)">{{ group.label }}</button></div><div v-if="activeNavGroup" class="tab-group-row sub-tabs"><button v-for="tab in activeNavGroup.tabs" :key="tab.key" class="tab-btn" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">{{ tab.label }}</button></div></nav>
    <main class="content">
      <section v-if="activeTab === 'dashboard'" class="grid home-grid"><article class="panel card feature-card"><span>账号</span><h3>{{ currentUser.username }}</h3><p>当前角色：{{ roleLabel(currentUser.role) }}</p></article><article class="panel card feature-card"><span>贡献视频</span><h3>{{ filteredContributions.length }}</h3><p>{{ isAdmin ? '可查看系统内全部贡献记录' : '可查看自己上传的贡献视频' }}</p></article><article class="panel card feature-card"><span>使用日志</span><h3>{{ isAdmin ? usageLogs.length : myUsageLogs.length }}</h3><p>{{ isAdmin ? '管理员可查看所有用户的操作日志' : '用户可查看自己的识别历史' }}</p></article><article class="panel card feature-card"><span>核心模型</span><h3>CNN-LSTM</h3><p>与当前后端模型推理流程保持一致。</p></article></section>
      <section v-if="activeTab === 'dashboard'" class="panel card" style="margin-top:18px"><div class="card-head"><div><h2>学习手语板块</h2><p>你可以从首页快速进入学习页，选择某个手语类别并观看示例视频。</p></div><button class="primary-btn" @click="activeTab='learning'">进入学习手语</button></div><div class="info-list"><div class="info-item"><strong>当前学习项</strong><span>{{ selectedLearning ? selectedLearning.name : '暂未选择' }}</span></div></div></section>
      <section v-if="activeTab === 'learning'" class="grid predict-grid"><article class="panel card learning-card"><div class="card-head"><div><h2>学习手语</h2><p>搜索句子、收藏常学内容，并在同一语义下切换不同示例视频。</p></div><button class="ghost-btn" @click="learningOnlyFavorites = !learningOnlyFavorites">{{ learningOnlyFavorites ? '显示全部' : '只看收藏' }}</button></div><div class="learning-search-row"><label class="field learning-search-field"><span>搜索手语句子</span><input v-model.trim="learningSearchKeyword" placeholder="输入关键词，例如：警察、妈妈、导演"></label><button class="ghost-btn learning-favorite-btn" :disabled="!selectedLearning" @click="toggleLearningFavorite">{{ isCurrentLearningFavorite ? '取消收藏' : '收藏句子' }}</button></div><div v-if="favoriteLearningMaterials.length" class="favorite-strip"><span class="favorite-strip-title">常学句子</span><div class="favorite-chip-row"><button v-for="item in favoriteLearningMaterials" :key="item.id" class="ghost-btn favorite-chip" @click="pickFavoriteLearning(item.id)">{{ item.name }}</button></div></div><label class="field"><span>选择手语类别</span><select v-model="selectedLearningId"><option v-for="item in filteredLearningMaterials" :key="item.id" :value="item.id">{{ item.name }}</option></select></label><div class="actions learning-controls"><button class="ghost-btn" :disabled="!learningVideoList.length" @click="goToPreviousLearningVideo">上一条</button><button class="ghost-btn" :disabled="isLearningRefreshing || learningVideoList.length <= 1" @click="refreshLearningVideo">{{ isLearningRefreshing ? '切换中...' : '随机切换' }}</button><button class="ghost-btn" :disabled="!learningVideoList.length" @click="goToNextLearningVideo">下一条</button></div><div v-if="selectedLearning" class="info-list learning-info-grid" style="margin-top:18px"><div class="info-item"><strong>{{ selectedLearning.name }}</strong><span>{{ selectedLearning.description }}</span></div><div class="info-item"><strong>收藏状态</strong><span>{{ isCurrentLearningFavorite ? '已加入常学句子' : '尚未收藏' }}</span></div><div class="info-item"><strong>类别编号</strong><span>{{ selectedLearning.label }}</span></div><div class="info-item"><strong>当前示例文件</strong><span>{{ currentLearningVideo ? currentLearningVideo.name : '--' }}</span></div><div class="info-item"><strong>当前进度</strong><span v-if="learningVideoList.length">{{ currentLearningVideoIndex + 1 }} / {{ learningVideoList.length }}</span><span v-else>暂无素材</span></div><div class="info-item"><strong>筛选结果</strong><span>当前匹配 {{ filteredLearningMaterials.length }} 个学习类别，共 {{ learningMaterials.length }} 个素材类别</span></div></div></article><article class="panel card"><div class="card-head"><div><h2>示例视频</h2><p>当前选中的学习视频会在这里播放。</p></div><span v-if="selectedLearning" class="tag">{{ selectedLearning.name }}</span></div><div class="video-box"><video v-if="currentLearningVideo" :src="selectedLearningVideoSrc" controls playsinline></video><div v-else class="empty-box"><div><strong>暂无学习视频</strong><span>请先选择一个手语类别。</span></div></div></div></article></section>
      <section v-if="!isAdmin && activeTab === 'predict'" class="grid predict-grid"><article class="panel card"><div class="card-head"><div><h2>模型识别</h2><p>上传视频后即可调用后端模型进行识别。</p></div></div><label class="upload-box"><input type="file" accept="video/*" @change="handlePredictFileChange"><span>选择识别视频</span><small>{{ fileMeta }}</small></label><div class="video-box"><video v-if="videoPreviewUrl" :src="videoPreviewUrl" controls playsinline></video><div v-else class="empty-box"><div><strong>等待导入视频</strong><span>可以上传本地视频，也可以先去实时录制。</span></div></div></div><div class="actions"><button class="secondary-btn" :disabled="isInitializing" @click="initPredictor">{{ isInitializing ? '初始化中...' : '初始化模型' }}</button><button class="primary-btn" :disabled="isPredicting" @click="initAndPredict">{{ isPredicting ? '识别中...' : '开始识别' }}</button></div></article><article class="panel card"><div class="card-head"><div><h2>识别结果</h2><p>显示识别文本、置信度和接口原始返回。</p></div></div><div class="result-box"><span>识别文本</span><h3>{{ resultText }}</h3></div><div class="progress-card"><div class="progress-head"><span>结果置信度</span><strong>{{ resultConfidence }}</strong></div><div class="progress-track"><div class="progress-bar" :style="{ width: confidenceWidth }"></div></div></div><div class="stats-grid"><div class="stat"><span>来源</span><strong>{{ resultSource }}</strong></div><div class="stat"><span>时间</span><strong>{{ resultTime }}</strong></div><div class="stat"><span>模型状态</span><strong>{{ predictorStatus }}</strong></div><div class="stat"><span>服务状态</span><strong>{{ serviceStatus }}</strong></div></div><div class="raw-box"><div class="card-head compact"><h3>接口原始返回</h3></div><pre>{{ rawResponse }}</pre></div></article></section>
      <section v-if="!isAdmin && activeTab === 'camera'" class="grid predict-grid"><article class="panel card"><div class="card-head"><div><h2>实时录制</h2><p>录制完成后会自动生成待识别视频，并跳转到识别页面。</p></div></div><div class="video-box camera-box"><video ref="cameraVideo" autoplay muted playsinline></video></div><div class="actions"><button class="secondary-btn" @click="openCamera">开启摄像头</button><button class="primary-btn" @click="toggleRecording">{{ isRecording ? '停止录制' : '开始录制' }}</button><button class="ghost-btn" @click="stopCamera">关闭摄像头</button></div></article><article class="panel card"><div class="stats-grid"><div class="stat"><span>摄像头</span><strong>{{ cameraState }}</strong></div><div class="stat"><span>录制状态</span><strong>{{ recordState }}</strong></div><div class="stat"><span>输入来源</span><strong>{{ currentSourceMode === 'camera' ? '实时录制' : '本地上传' }}</strong></div><div class="stat"><span>当前用户</span><strong>{{ currentUser.username }}</strong></div></div></article></section>
      <section v-if="!isAdmin && activeTab === 'contribute'" class="grid contribute-page"><article class="panel card"><div class="card-head"><div><h2>贡献视频</h2><p>请先在下方两种方式中任选一种准备视频，再填写手语含义并提交。</p></div></div><div class="contribute-workspace"><div class="contribute-main"><div class="info-list compact-info"><div class="info-item"><strong>当前来源</strong><span>{{ contributionSource }}</span></div><div class="info-item"><strong>视频状态</strong><span>{{ contributionMeta }}</span></div></div><div class="contribute-methods"><section class="contribute-method-card"><div class="method-head"><span class="method-index">①</span><div><h3>文件上传</h3><p>适合已经拍好的手语视频，直接选择本地文件即可。</p></div></div><label class="upload-box contribute-upload-box"><input type="file" accept="video/*" @change="handleContributionFileChange"><span>上传本地视频文件</span><small>支持 mp4、avi、mov、webm 等常见格式</small></label></section><section class="contribute-method-card contribute-method-camera"><div class="method-head"><span class="method-index">②</span><div><h3>录制上传</h3><p>适合现场拍摄。先开启摄像头，再开始录制，完成后会自动生成待提交视频。</p></div></div><div class="actions contribute-camera-actions"><button class="secondary-btn" @click="openContributionCamera">开启录制摄像头</button><button class="primary-btn" @click="toggleContributionRecording">{{ isContributionRecording ? '停止现场录制' : '开始现场录制' }}</button><button class="ghost-btn" @click="stopContributionCamera">关闭录制摄像头</button></div></section></div><section class="contribute-submit-card"><div class="method-head"><span class="method-index">③</span><div><h3>填写说明并提交</h3><p>确认右侧预览无误后，填写这段手语表达的意思，再提交到系统。</p></div></div><label class="field textarea-field"><span>这段手语视频表达的意思</span><textarea v-model="contributionForm.note" rows="4" placeholder="例如：这段手语表达的是“你好，很高兴认识你”"></textarea></label><div class="actions"><button class="primary-btn" @click="submitContribution">提交贡献视频</button><button class="ghost-btn" @click="resetContributionForm">清空当前视频</button></div></section></div><div class="contribute-preview"><section class="preview-panel"><div class="preview-panel-head"><h3>录制画面</h3><span>用于现场录制</span></div><div class="video-box camera-box preview-tight"><video ref="contributionCameraVideo" autoplay muted playsinline></video></div></section><div class="stats-grid contribution-stats"><div class="stat"><span>摄像头</span><strong>{{ contributionCameraState }}</strong></div><div class="stat"><span>录制状态</span><strong>{{ contributionRecordState }}</strong></div><div class="stat"><span>视频来源</span><strong>{{ contributionSource }}</strong></div><div class="stat"><span>当前用户</span><strong>{{ currentUser.username }}</strong></div></div><section class="preview-panel"><div class="preview-panel-head"><h3>待提交视频预览</h3><span>上传或录制完成后显示</span></div><div class="video-box preview-tight"><video v-if="contributionFileUrl" :src="contributionFileUrl" controls playsinline></video><div v-else class="empty-box"><div><strong>等待贡献视频</strong><span>上传或录制完成后，这里会显示预览。</span></div></div></div></section></div></div></article><article class="panel card"><div class="card-head"><div><h2>我的贡献记录</h2><p>这里显示当前用户已经上传的贡献视频及其表达意思。</p></div></div><div class="table-wrap"><table><thead><tr><th>时间</th><th>文件名</th><th>表达意思</th></tr></thead><tbody><tr v-for="item in filteredContributions" :key="item.id"><td>{{ item.timestamp }}</td><td>{{ item.original_name }}</td><td>{{ item.note || '--' }}</td></tr></tbody></table></div></article></section>
      <section v-if="!isAdmin && activeTab === 'my-usage'" class="panel card"><div class="card-head"><div><h2>我的使用记录</h2><p>记录当前用户在什么时间进行了什么操作，以及对应内容。</p></div><button class="ghost-btn" @click="fetchMyUsageLogs">刷新记录</button></div><div class="table-wrap"><table><thead><tr><th>时间</th><th>操作</th><th>来源</th><th>文件</th><th>内容</th><th>置信度</th></tr></thead><tbody><tr v-for="item in myUsageLogs" :key="item.id"><td>{{ item.timestamp }}</td><td>{{ actionLabel(item.action) }}</td><td>{{ item.source }}</td><td>{{ item.file_name }}</td><td>{{ item.content }}</td><td>{{ item.confidence }}</td></tr></tbody></table></div></section>
      <section v-if="isAdmin && activeTab === 'users'" class="grid predict-grid"><article class="panel card"><div class="card-head"><div><h2>用户管理</h2><p>管理员可以新增、修改和删除用户。</p></div></div><div class="form-grid"><label class="field"><span>用户名</span><input v-model="userForm.username" placeholder="请输入用户名"></label><label class="field"><span>显示名称</span><input v-model="userForm.display_name" placeholder="请输入显示名称"></label><label class="field"><span>密码</span><input v-model="userForm.password" type="password" placeholder="新增或重置密码时填写"></label><label class="field"><span>角色</span><select v-model="userForm.role"><option value="user">用户</option><option value="admin">管理员</option></select></label></div><div class="actions"><button class="primary-btn" @click="saveUser">{{ userForm.id ? '更新用户' : '新增用户' }}</button><button class="ghost-btn" @click="resetUserForm">重置表单</button></div></article><article class="panel card"><div class="card-head"><div><h2>用户列表</h2><p>管理员可对用户进行增删改。</p></div><button class="ghost-btn" @click="fetchUsers">刷新用户</button></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>用户名</th><th>显示名</th><th>角色</th><th>创建时间</th><th>操作</th></tr></thead><tbody><tr v-for="user in adminUsers" :key="user.id"><td>{{ user.id }}</td><td>{{ user.username }}</td><td>{{ user.display_name }}</td><td>{{ roleLabel(user.role) }}</td><td>{{ user.created_at }}</td><td class="table-actions"><button class="ghost-btn small-btn" @click="editUser(user)">编辑</button><button class="ghost-btn small-btn danger-btn" @click="deleteUser(user)">删除</button></td></tr></tbody></table></div></article></section>
      <section v-if="isAdmin && activeTab === 'usage'" class="panel card"><div class="card-head"><div><h2>用户使用日志</h2><p>管理员可以查看用户在什么时间执行了什么操作。</p></div><button class="ghost-btn" @click="fetchUsageLogs">刷新日志</button></div><div class="table-wrap"><table><thead><tr><th>时间</th><th>用户</th><th>角色</th><th>操作</th><th>来源</th><th>文件</th><th>内容</th><th>置信度</th></tr></thead><tbody><tr v-for="item in usageLogs" :key="item.id"><td>{{ item.timestamp }}</td><td>{{ item.username }}</td><td>{{ roleLabel(item.role) }}</td><td>{{ actionLabel(item.action) }}</td><td>{{ item.source }}</td><td>{{ item.file_name }}</td><td>{{ item.content }}</td><td>{{ item.confidence }}</td></tr></tbody></table></div></section>
      <section v-if="isAdmin && activeTab === 'contributions'" class="panel card"><div class="card-head"><div><h2>视频贡献记录</h2><p>管理员可以查看所有用户上传的贡献视频及其描述。</p></div><button class="ghost-btn" @click="fetchContributions">刷新贡献记录</button></div><div class="table-wrap"><table><thead><tr><th>时间</th><th>用户</th><th>原始文件名</th><th>保存文件名</th><th>表达意思</th></tr></thead><tbody><tr v-for="item in contributions" :key="item.id"><td>{{ item.timestamp }}</td><td>{{ item.username }}</td><td>{{ item.original_name }}</td><td>{{ item.file_name }}</td><td>{{ item.note || '--' }}</td></tr></tbody></table></div></section>
      <section v-if="!isAdmin && activeTab === 'about'" class="grid"><article class="panel card"><div class="card-head"><div><h2>账号管理</h2></div></div><div class="stats-grid account-summary-grid"><div class="stat"><span>当前用户名</span><strong>{{ currentUser.username }}</strong></div><div class="stat"><span>当前昵称</span><strong>{{ currentUser.display_name || '--' }}</strong></div><div class="stat"><span>账号角色</span><strong>{{ roleLabel(currentUser.role) }}</strong></div><div class="stat"><span>修改提示</span><strong>{{ accountMessage }}</strong></div></div><div class="form-grid account-form-grid"><label class="field"><span>用户名</span><input :value="profileForm.username" disabled></label><label class="field"><span>用户昵称</span><input v-model="profileForm.display_name" placeholder="请输入新的昵称"></label><label class="field"><span>当前密码</span><input v-model="profileForm.current_password" type="password" placeholder="保存修改时必须填写"></label><label class="field"><span>新密码</span><input v-model="profileForm.new_password" type="password" placeholder="不修改密码可留空"></label><label class="field account-field-wide"><span>确认新密码</span><input v-model="profileForm.confirm_password" type="password" placeholder="再次输入新密码"></label></div><div class="actions"><button class="primary-btn" @click="updateAccount">保存账号信息</button><button class="ghost-btn" @click="syncProfileForm">重置表单</button></div></article></section>
      <section v-if="isAdmin && activeTab === 'about'" class="grid home-grid"><article class="panel card wide-card"><div class="card-head"><div><h2>系统说明</h2><p>当前系统已经具备登录、角色控制、模型使用、用户管理、贡献视频和日志追踪能力。</p></div></div><div class="info-list"><div class="info-item"><strong>前端</strong><span>Vue 3 原生模块模式</span></div><div class="info-item"><strong>后端</strong><span>Flask + 本地 JSON 存储 + 视频文件保存</span></div><div class="info-item"><strong>管理员</strong><span>管理用户、查看日志、查看贡献视频记录</span></div><div class="info-item"><strong>用户</strong><span>执行识别、学习手语、查看历史、上传贡献视频</span></div></div></article><article class="panel card wide-card"><div class="card-head"><div><h2>系统日志</h2><p>记录当前前端中的主要操作过程。</p></div></div><pre class="log-view">{{ logs.join('\\n') }}</pre></article></section>
    </main>
  </template>
</div>`,
};
