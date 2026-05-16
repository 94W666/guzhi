// pages/index/index.js — 基金数据分析主页
const api = require("../../utils/api");
const app = getApp();

function formatScale(v) {
  if (!v || v <= 0) return "";
  return v >= 1 ? "规模 " + v.toFixed(2) + "亿" : "规模 " + (v * 10000).toFixed(0) + "万";
}

// 指标解读文案（复用 Web 版）
const METRIC_INFO = {
  annual_return: {
    title: "年化收益率 (Annualized Return)",
    body: "含义：假设基金按当前周期内的复利速度增长，一年能获得的收益率（CAGR）。\n\n公式：(期末净值 / 期初净值)^(365/天数) - 1\n\n评级参考：\n>15% 优秀\n8~15% 良好\n3~8% 一般\n<3% 偏低"
  },
  max_drawdown: {
    title: "最大回撤 (Max Drawdown)",
    body: "含义：在选定周期内，从净值最高点到最低点的最大亏损幅度。\n\n公式：遍历每日净值，(当日净值 - 此前最高净值) / 此前最高净值，取最小值。\n\n评级参考：\n<10% 优秀\n10~20% 良好\n20~30% 一般\n>30% 较高"
  },
  volatility: {
    title: "波动率 (Volatility)",
    body: "含义：基金日收益率的标准差年化值，衡量价格的波动剧烈程度。\n\n公式：std(日收益率) × √252\n\n评级参考：\n<15% 低波动\n15~25% 中等\n>25% 高波动"
  },
  sharpe: {
    title: "夏普比率 (Sharpe Ratio)",
    body: "含义：每承担一单位风险能获得多少超额收益。\n\n公式：(年化收益 - 无风险利率) / 波动率，无风险利率默认 2.5%。\n\n评级参考：\n>2.0 优秀\n1.0~2.0 良好\n0.5~1.0 一般\n<0.5 较差"
  },
  pe_ratio: {
    title: "PE 比率 (市盈率)",
    body: "含义：基金持仓股票的加权市盈率（调和平均），反映市场对持仓资产的估值水平。\n\n公式：1 / Σ(权重_i / PE_i)\n\n评级参考：\n<15 低估\n15~25 合理\n25~30 偏贵\n>30 高估值"
  },
  calmar: {
    title: "Calmar 比率",
    body: "含义：年化收益率与最大回撤的比值，衡量「收益/痛苦」的性价比。\n\n公式：年化收益率 / |最大回撤|\n\n评级参考：\n>3.0 优秀\n1.0~3.0 良好\n0.5~1.0 一般\n<0.5 较差"
  },
  win_rate: {
    title: "胜率 (Win Rate)",
    body: "含义：日收益率为正的天数占总交易日的比例，反映上涨的持续性。\n\n公式：上涨天数 / 总交易日数\n\n参考：\n>60% 强上涨趋势\n50~60% 中等\n<50% 偏弱"
  },
  recovery_days: {
    title: "回撤修复天数",
    body: "含义：从最大回撤的谷底到净值回到前高所需的天数。衡量基金从大跌中恢复的速度。\n\n数值越小说明基金修复能力越强。\n\n若显示「未修复」，说明当前净值仍未回到最大回撤前的峰值。"
  },
};

Page({
  data: {
    // 状态
    fund: null,
    metrics: null,
    holdings: [],
    activePeriod: "1y",
    loading: false,
    searchQuery: "",
    searchResults: [],
    favorites: [],
    isFavorited: false,

    // 指标显示
    metricReturn: null,
    metricReturnFmt: "—",
    metricDrawdown: null,
    metricDrawdownFmt: "—",
    metricVol: null,
    metricVolFmt: "—",
    metricSharpe: null,
    metricSharpeFmt: "—",
    peRatio: null,
    peRatioFmt: "—",
    metricCalmar: null,
    metricCalmarFmt: "—",
    metricWinRate: null,
    metricWinRateFmt: "—",
    metricRecoveryFmt: "—",
    mddPeak: "",
    mddTrough: "",

    // DCA
    dca: null,
    dcaAmount: 1000,
    dcaYears: 3,

    // Modal
    modalVisible: false,
    modalTitle: "",
    modalBody: "",
  },

  // -----------------------------------------------------------------------
  // 生命周期
  // -----------------------------------------------------------------------
  onLoad() {
    this._loadFavorites();
  },

  // -----------------------------------------------------------------------
  // 收藏 / 自选
  // -----------------------------------------------------------------------
  _loadFavorites() {
    try {
      const favs = wx.getStorageSync("favorites") || [];
      this.setData({ favorites: favs });
    } catch (e) {
      this.setData({ favorites: [] });
    }
  },

  _saveFavorites(favs) {
    wx.setStorageSync("favorites", favs);
    this.setData({ favorites: favs });
    // 同步更新当前基金的收藏状态
    if (this.data.fund) {
      const isFav = favs.some(f => f.code === this.data.fund.code);
      this.setData({ isFavorited: isFav });
    }
  },

  toggleFavorite() {
    if (!this.data.fund) return;
    let favs = [...this.data.favorites];
    const code = this.data.fund.code;

    if (this.data.isFavorited) {
      favs = favs.filter(f => f.code !== code);
    } else {
      favs.push({
        code: code,
        name: this.data.fund.name,
        fund_type: this.data.fund.fund_type,
      });
    }
    this._saveFavorites(favs);
  },

  loadFavorite(e) {
    const code = e.currentTarget.dataset.code;
    this.loadFund(code);
  },

  removeFavorite(e) {
    const code = e.currentTarget.dataset.code;
    const name = e.currentTarget.dataset.name;
    wx.showModal({
      title: "删除自选",
      content: "将 " + name + " 从自选列表中移除？",
      success: (res) => {
        if (res.confirm) {
          const favs = this.data.favorites.filter(f => f.code !== code);
          this._saveFavorites(favs);
          wx.showToast({ title: "已删除", icon: "none", duration: 1000 });
        }
      }
    });
  },

  // -----------------------------------------------------------------------
  // 搜索
  // -----------------------------------------------------------------------
  onSearchInput(e) {
    this.setData({ searchQuery: e.detail.value, searchResults: [] });
  },

  async onSearchConfirm(e) {
    const q = (e.detail && e.detail.value || this.data.searchQuery).trim();
    if (!q) return;
    // 先搜索，有结果就直接展示下拉供选择
    try {
      const data = await api.get("/api/funds/search?q=" + encodeURIComponent(q));
      const results = data.results || [];
      if (results.length === 1) {
        // 唯一匹配直接加载
        this.selectFund({ currentTarget: { dataset: { code: results[0].code } } });
      } else if (results.length > 0) {
        // 多个结果，展示下拉列表
        this.setData({ searchResults: results });
      } else {
        // 无结果
        this.setData({ searchResults: [] });
        wx.showToast({ title: "未找到匹配的基金", icon: "none" });
      }
    } catch (e) {
      wx.showToast({ title: "搜索失败", icon: "none" });
    }
  },

  // -----------------------------------------------------------------------
  // 基金加载
  // -----------------------------------------------------------------------
  selectFund(e) {
    const code = e.currentTarget.dataset.code;
    this.setData({ searchResults: [], activePeriod: "1y" });
    this.loadFund(code);
  },

  async loadFund(code) {
    // 取消上一次加载中未完成的请求
    this._currentCode = code;
    this.setData({ loading: true, fund: null, dca: null });
    try {
      const data = await api.get("/api/funds/" + code);
      if (code !== this._currentCode) return; // 防止竞态：请求返回时已切换基金
      const isFav = this.data.favorites.some(f => f.code === data.fund.code);
      this.setData({
        fund: data.fund,
        metrics: data.metrics,
        holdings: data.holdings || [],
        navStart: (data.data_summary && data.data_summary.nav_start) || null,
        scaleFmt: formatScale(data.fund.scale),
        loading: false,
        isFavorited: isFav,
      });
      // fund_detail 已返回全部指标含 PE，直接显示
      this._updateMetrics();
      // 后台加载 DCA
      this._loadDca(code);
    } catch (e) {
      this.setData({ loading: false });
      wx.showToast({ title: "加载失败: " + e.message, icon: "none" });
    }
  },

  // -----------------------------------------------------------------------
  // 指标更新
  // -----------------------------------------------------------------------
  _updateMetrics() {
    const m = this.data.metrics;
    if (!m) return;
    const p = this.data.activePeriod === "all" ? "since_inception" : this.data.activePeriod;

    const ret = m.returns?.[p];
    const dd = m.max_drawdown?.[p];
    const vol = m.volatility?.[this.data.activePeriod];
    const sharpe = m.sharpe?.[this.data.activePeriod];
    const pe = m.pe_ratio?.pe;
    const calmar = m.calmar?.[this.data.activePeriod];
    const win = m.win_rate?.[this.data.activePeriod];
    const recovery = m.recovery_days?.[p];

    const fmtPct = (v) => v != null ? (v * 100).toFixed(2) + "%" : "—";
    const fmtNum = (v, d = 2) => v != null ? v.toFixed(d) : "—";

    this.setData({
      metricReturn: ret != null ? ret : null, metricReturnFmt: fmtPct(ret),
      metricDrawdown: dd?.mdd != null ? dd.mdd : null, metricDrawdownFmt: fmtPct(dd?.mdd),
      mddPeak: dd?.peak_date || "", mddTrough: dd?.trough_date || "",
      metricVol: vol != null ? vol : null, metricVolFmt: fmtPct(vol),
      metricSharpe: sharpe != null ? sharpe : null, metricSharpeFmt: fmtNum(sharpe),
      peRatio: pe != null ? pe : null, peRatioFmt: pe != null ? pe.toFixed(1) : "—",
      metricCalmar: calmar != null ? calmar : null, metricCalmarFmt: fmtNum(calmar),
      metricWinRate: win != null ? win : null, metricWinRateFmt: fmtPct(win),
      metricRecoveryFmt: recovery
        ? (recovery.recovered ? recovery.recovery_days + "天" : "未修复")
        : "—",
    });
  },

  // -----------------------------------------------------------------------
  // Period 切换
  // -----------------------------------------------------------------------
  async switchPeriod(e) {
    const period = e.currentTarget.dataset.period;
    this.setData({ activePeriod: period });

    if (!this.data.fund) return;

    // fund_detail 已返回全部周期指标，直接从缓存计算即可（零网络）
    this._updateMetrics();
  },

  // -----------------------------------------------------------------------
  // DCA 参数输入
  // -----------------------------------------------------------------------
  onDcaAmountInput(e) {
    this.setData({ dcaAmount: e.detail.value });
  },
  onDcaYearsInput(e) {
    this.setData({ dcaYears: e.detail.value });
  },
  recalcDca() {
    if (!this.data.fund) return;
    const amount = parseInt(this.data.dcaAmount) || 1000;
    const years = parseInt(this.data.dcaYears) || 3;
    const yearsClamped = years < 1 ? 1 : years > 10 ? 10 : years;
    this.setData({ dcaAmount: amount, dcaYears: yearsClamped });
    this._loadDca(this.data.fund.code);
  },

  // -----------------------------------------------------------------------
  // DCA 回测数据
  // -----------------------------------------------------------------------
  async _loadDca(code) {
    if (code !== this._currentCode) return; // 已切换到其他基金
    const amount = parseInt(this.data.dcaAmount) || 1000;
    const years = parseInt(this.data.dcaYears) || 3;
    try {
      const data = await api.get("/api/funds/" + code + "/dca?amount=" + amount + "&years=" + years);
      if (code !== this._currentCode) return; // 请求返回时已切换
      const costAboveNav = data.avg_cost_per_share > data.current_nav;
      const gapPct = Math.abs((data.avg_cost_per_share - data.current_nav) / data.current_nav * 100);
      const dcaWins = data.total_return_pct > data.lump_sum.return_pct;

      // 检查数据是否足够长：请求 N 年但基金只有更短的历史
      const actualMonths = data.total_months || 0;
      const expectedMonths = years * 12;
      const dataInsufficient = actualMonths < expectedMonths - 1; // 允许差1个月

      this.setData({
        dca: {
          ...data,
          dataInsufficient: dataInsufficient,
          requestedYears: years,
          total_invested_wan: (data.total_invested / 10000).toFixed(2),
          final_value_wan: (data.final_value / 10000).toFixed(2),
          total_return_pct_fmt: data.total_return_pct.toFixed(1),
          annualized_return_pct_fmt: data.annualized_return_pct.toFixed(1),
          lump_return_fmt: (data.lump_sum.return_pct > 0 ? "+" : "") + data.lump_sum.return_pct.toFixed(1),
          avg_cost: data.avg_cost_per_share.toFixed(4),
          current_nav: data.current_nav.toFixed(4),
          // 成本 vs 净值 解读
          cost_above_nav: costAboveNav,
          cost_nav_desc: costAboveNav
            ? "当前净值低于平均成本 " + gapPct.toFixed(1) + "%，持仓处于浮亏状态。但下跌中定投意味着你在以更低的净值买入。"
            : "当前净值高于平均成本 " + gapPct.toFixed(1) + "%，定投持仓处于盈利状态。",
          // 定投 vs 一次性 解读
          vs_lump_desc: dcaWins
            ? "该时段内市场整体走低或震荡，定投通过分批买入分摊了成本，最终跑赢了一次性买入。"
            : "该时段内市场整体走高，前期买入成本更低，一次性买入跑赢了定投。定投是对不确定性的应对——没有人事先知道哪种更好。",
        }
      });
    } catch (e) {
      // DCA 加载失败不报错
    }
  },

  // -----------------------------------------------------------------------
  // Modal
  // -----------------------------------------------------------------------
  showMetricInfo(e) {
    const key = e.currentTarget.dataset.key;
    const info = METRIC_INFO[key];
    if (!info) return;
    this.setData({
      modalVisible: true,
      modalTitle: info.title,
      modalBody: info.body
    });
  },

  closeModal() {
    this.setData({ modalVisible: false });
  },

  // -----------------------------------------------------------------------
  // 返回首页
  // -----------------------------------------------------------------------
  goHome() {
    this.setData({
      fund: null, metrics: null, holdings: [],
      navStart: null, scaleFmt: "",
      dca: null, isFavorited: false,
      searchQuery: "", searchResults: [],
      activePeriod: "1y",
    });
  }
});
