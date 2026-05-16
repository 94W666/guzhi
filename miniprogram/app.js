App({
  globalData: {
    // === 开发模式 ===
    // 本地跑 python main.py，微信开发者工具勾选"不校验合法域名"
    // - useCloud: false
    // - apiBase: "http://localhost:8000"
    //
    // === 云托管上线 ===
    // 1. 腾讯云开发控制台 → 云托管 → 新建服务 → 上传代码包
    // 2. 环境变量配置 DATABASE_URL=mysql+pymysql://user:pass@host/db
    // 3. 改下方配置：
    useCloud: false,
    apiBase: "http://localhost:8000",

    // 云托管配置（useCloud: true 时生效）
    cloudEnv: "",        // 云开发环境 ID，如 "prod-xxx"
    cloudService: "",    // 云托管服务名
  },

  onLaunch() {
    if (this.globalData.useCloud && this.globalData.cloudEnv) {
      wx.cloud.init({ env: this.globalData.cloudEnv });
    }
  }
});
