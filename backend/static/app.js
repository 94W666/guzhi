/**
 * Fund Analysis Dashboard
 */

// ---------------------------------------------------------------------------
// Metric explanations
// ---------------------------------------------------------------------------
const METRIC_INFO = {
    annual_return: {
        title: "年化收益率 (Annualized Return)",
        body: `
            <p><strong>含义：</strong>假设基金按当前周期内的复利速度增长，一年能获得的收益率。又称<em>复合年化增长率 (CAGR)</em>。</p>
            <p><strong>公式：</strong>(期末净值 / 期初净值)<sup>(365/天数)</sup> &minus; 1，使用累计净值（含分红再投资）。</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&gt; 15%</td><td class="green">优秀</td></tr>
                <tr><td>8% ~ 15%</td><td class="blue">良好</td></tr>
                <tr><td>3% ~ 8%</td><td>一般</td></tr>
                <tr><td>&lt; 3%</td><td class="red">偏低</td></tr>
            </table>
            <p class="note">注意：高收益往往伴随高风险，需结合回撤和波动率综合判断。</p>
        `,
    },
    max_drawdown: {
        title: "最大回撤 (Max Drawdown)",
        body: `
            <p><strong>含义：</strong>在选定周期内，从净值最高点买入到最低点卖出的最大亏损幅度。是衡量基金<em>极端风险</em>的最核心指标。</p>
            <p><strong>公式：</strong>遍历每日净值，计算 (当日净值 &minus; 此前最高净值) / 此前最高净值，取最小值。</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&lt; 10%</td><td class="green">优秀 — 抗跌能力强</td></tr>
                <tr><td>10% ~ 20%</td><td class="blue">良好</td></tr>
                <tr><td>20% ~ 30%</td><td>一般 — 需关注风险</td></tr>
                <tr><td>&gt; 30%</td><td class="red">较高 — 波动较大</td></tr>
            </table>
            <p class="note">回撤反映了基金经理在市场下行时的风险控制能力，以及投资者可能承受的最大"浮亏"。历史最大回撤不代表未来最坏情况，但可作为压力测试参考。</p>
        `,
    },
    volatility: {
        title: "波动率 (Volatility)",
        body: `
            <p><strong>含义：</strong>基金日收益率的标准差年化值。衡量基金价格的<em>波动剧烈程度</em>，反映不确定性。</p>
            <p><strong>公式：</strong>std(日收益率) &times; &radic;252，252为年交易日数。</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&lt; 15%</td><td class="green">低波动 — 走势平缓</td></tr>
                <tr><td>15% ~ 25%</td><td class="blue">中等波动</td></tr>
                <tr><td>&gt; 25%</td><td class="red">高波动 — 价格跳跃剧烈</td></tr>
            </table>
            <p class="note">波动率本身不区分上涨和下跌波动，高波动率意味着基金价格变化活跃（可能大涨也可能大跌）。对于长期投资者，适度的高波动可以接受；对于保守投资者，应偏好低波动。</p>
        `,
    },
    sharpe: {
        title: "夏普比率 (Sharpe Ratio)",
        body: `
            <p><strong>含义：</strong>每承担一单位风险（波动）能获得多少<em>超额收益</em>（超过无风险利率的部分）。是衡量基金<em>风险调整后收益</em>的最经典指标。</p>
            <p><strong>公式：</strong>(年化收益率 &minus; 无风险利率) / 年化波动率，无风险利率默认 2.5%（中国10年期国债收益率）。</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&gt; 2.0</td><td class="green">优秀 — 风险收益比很高</td></tr>
                <tr><td>1.0 ~ 2.0</td><td class="blue">良好</td></tr>
                <tr><td>0.5 ~ 1.0</td><td>一般</td></tr>
                <tr><td>&lt; 0.5</td><td class="red">较差 — 承担风险未获得足够回报</td></tr>
                <tr><td>&lt; 0</td><td class="red">负值 — 收益低于无风险利率</td></tr>
            </table>
            <p class="note">夏普比率的核心思想：同样赚 10%，波动 5% 的基金比波动 20% 的基金更优秀。夏普比率只惩罚波动本身（包括向上波动），Sortino 比率对此做了改进。</p>
        `,
    },
    pe_ratio: {
        title: "PE 比率 (市盈率)",
        body: `
            <p><strong>含义：</strong>基金持仓股票的加权市盈率（调和平均）。反映市场对基金所持资产的<em>估值水平</em>。</p>
            <p><strong>公式：</strong>1 / &Sigma;(持仓权重<sub>i</sub> / PE<sub>i</sub>)，即加权调和平均。每个持仓的 PE 为 TTM（最近12个月滚动市盈率）。</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&lt; 15</td><td class="green">低估 — 可能有安全边际</td></tr>
                <tr><td>15 ~ 25</td><td class="blue">合理估值</td></tr>
                <tr><td>25 ~ 30</td><td>偏贵 — 需关注成长性</td></tr>
                <tr><td>&gt; 30</td><td class="red">高估值 — 风险溢价较低</td></tr>
            </table>
            <p class="note">PE 指标更适合指数型基金。科技类基金 PE 通常偏高（因为成长预期高），应与同类基金或指数比较，不宜跨行业直接对比。当前 PE 数据来自东方财富美股行情，部分股票可能缺失 PE 数据。</p>
        `,
    },
    calmar: {
        title: "Calmar 比率",
        body: `
            <p><strong>含义：</strong>年化收益率与最大回撤的比值。衡量<em>单位最大回撤能产出多少收益</em>，是评估"收益/痛苦"性价比的核心指标。</p>
            <p><strong>公式：</strong>年化收益率 / |最大回撤|</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&gt; 3.0</td><td class="green">优秀 — 高收益低回撤</td></tr>
                <tr><td>1.0 ~ 3.0</td><td class="blue">良好</td></tr>
                <tr><td>0.5 ~ 1.0</td><td>一般</td></tr>
                <tr><td>&lt; 0.5</td><td class="red">较差 — 回撤大收益小</td></tr>
            </table>
            <p class="note">Calmar 比率特别适合评估"能不能扛得住"的心态：如果一只基金回撤 30% 才赚 10% 年化（Calmar=0.33），多数投资者难以坚持持有。Calmar 越大，投资者持有体验越好。</p>
        `,
    },
    win_rate: {
        title: "胜率 (Win Rate)",
        body: `
            <p><strong>含义：</strong>在选定周期内，基金日收益率为正的天数占总交易日的比例。反映基金<em>上涨的持续性</em>。</p>
            <p><strong>公式：</strong>上涨天数 / 总交易日数</p>
            <table class="info-table">
                <tr><th>区间</th><th>评级</th></tr>
                <tr><td>&gt; 60%</td><td class="green">强上涨趋势</td></tr>
                <tr><td>50% ~ 60%</td><td class="blue">中等偏上</td></tr>
                <tr><td>&lt; 50%</td><td class="red">偏弱 — 跌多涨少</td></tr>
            </table>
            <p class="note">胜率只统计天数，不考虑涨幅大小。一只基金可能"跌三天涨一天"但一天涨幅覆盖三天跌幅（低胜率高盈亏比），或反之。需结合收益和回撤综合评判。</p>
        `,
    },
    nav_chart: {
        title: "净值走势 — 单位净值 vs 累计净值",
        body: `
            <p><strong>蓝色实线 — 单位净值：</strong>每份基金份额的当日价格。它是投资者日常买卖基金的<em>实际成交价格</em>，不考虑历史分红的影响。</p>
            <p><strong>绿色虚线 — 累计净值：</strong>单位净值 + 历史上所有分红的复权还原。它反映了<em>包含分红再投资</em>后的真实增长轨迹。</p>
            <p><strong>为什么看累计净值？</strong>假设一只基金从 1 元涨到 2 元后每份分红 1 元，单位净值回到 1 元——看起来好像没涨。但累计净值是 2 元，真实回报是翻倍。因此<em>计算年化收益、最大回撤等指标均使用累计净值</em>。</p>
            <p class="note">两条线差距越大，说明基金历史分红越多。</p>
        `,
    },
    drawdown_chart: {
        title: "回撤曲线 (Drawdown)",
        body: `
            <p><strong>含义：</strong>从净值历史最高点算起，当前净值距离那个峰值的跌幅。红色面积图展示的是"如果我在最高点买入，现在亏了多少"。</p>
            <p><strong>为什么重要？</strong>最大回撤是衡量基金<em>极端风险</em>的核心指标。两只基金可能有相同的年化收益，但回撤 10% 的持有体验远好于回撤 30% 的。</p>
            <p><strong>怎么看：</strong>回撤曲线越贴近零轴越好。大幅下探的深谷意味着基金曾经历严重下跌，投资者若在谷底割肉则永久锁定亏损。</p>
            <p class="note">图表使用累计净值计算回撤。点击"最大回撤"指标卡片可查看具体评级标准。</p>
        `,
    },
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state = {
    fund: null,
    metrics: null,
    holdings: [],
    dataSummary: null,
    activePeriod: "1y",
    loading: false,
    searchQuery: "",
    searchResults: [],
    searchTimer: null,
    navChart: null,
    ddChart: null,
    navHistory: [],
    navHistoryAll: [],  // full NAV history cached once, filtered client-side
    dca: null,
    dcaChart: null,
    _loadingFund: false,
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
const API = {
    async get(url) {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
    async search(q) {
        const resp = await fetch(`/api/funds/search?q=${encodeURIComponent(q)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data.results || [];
    },
};

function formatPct(v) {
    if (v == null || isNaN(v)) return "\u2014";
    return (v * 100).toFixed(2) + "%";
}

function formatNum(v, d = 2) {
    if (v == null || isNaN(v)) return "\u2014";
    return v.toFixed(d);
}

function esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------
function openMetricInfo(key) {
    const info = METRIC_INFO[key];
    if (!info) return;
    document.getElementById("modalTitle").innerHTML = info.title;
    document.getElementById("modalBody").innerHTML = info.body + '<p class="metric-disclaimer">以上为数据计算结果，仅供参考</p>';
    document.getElementById("metricModal").classList.add("active");
}
function closeModal() {
    document.getElementById("metricModal").classList.remove("active");
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function loadFund(code) {
    if (state._loadingFund) return;
    state._loadingFund = true;
    state.loading = true;
    state.navHistory = [];
    state.navHistoryAll = [];
    state.dca = null;
    _lastChartPeriod = null;
    render();

    try {
        // Fetch fund detail
        const data = await API.get(`/api/funds/${code}`);
        state.fund = data.fund;
        state.metrics = data.metrics;
        state.holdings = data.holdings || [];
        state.dataSummary = data.data_summary;
        state.searchQuery = code;
        state.searchResults = [];
        document.title = `${data.fund.name} - 基金分析`;
        // Load full NAV history once (cached for client-side period filtering)
        // and DCA in background (both slower, don't block first render)
        prefetchNavAll(code);
        loadDca(code);
    } catch (err) {
        console.error(err);
        alert('加载失败: ' + err.message);
    } finally {
        state._loadingFund = false;
        state.loading = false;
        render();
    }
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------
function buildNavChart(navData) {
    const ctx = document.getElementById("navChart");
    if (!ctx) return;
    if (state.navChart) { state.navChart.destroy(); state.navChart = null; }
    if (!navData || !navData.length) return;

    const labels = navData.map(d => d.nav_date);
    state.navChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "单位净值", data: navData.map(d => d.unit_nav), borderColor: "#4a90d9", backgroundColor: "rgba(74,144,217,0.05)", borderWidth: 2, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "累计净值", data: navData.map(d => d.cumulative_nav), borderColor: "#27ae60", borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0, fill: false, tension: 0.1 },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { position: "top", labels: { usePointStyle: true, boxWidth: 8, padding: 16, font: { size: 11 } } },
                tooltip: { callbacks: { label: ctx => ctx.dataset.label + ": " + ctx.parsed.y.toFixed(4) } },
            },
            scales: {
                x: { display: true, ticks: { maxTicksLimit: 12, font: { size: 10 } } },
                y: { display: true, ticks: { font: { size: 10 } } },
            },
        },
    });
}

function buildDrawdownChart(navData) {
    const ctx = document.getElementById("drawdownChart");
    if (!ctx) return;
    if (state.ddChart) { state.ddChart.destroy(); state.ddChart = null; }
    if (!navData || !navData.length) return;

    const labels = [], ddData = [];
    let peak = -Infinity;
    for (const d of navData) {
        const nav = d.cumulative_nav || d.unit_nav;
        if (nav > peak) peak = nav;
        labels.push(d.nav_date);
        ddData.push(peak > 0 ? (nav - peak) / peak * 100 : 0);
    }
    state.ddChart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets: [{ label: "回撤 %", data: ddData, borderColor: "#e74c3c", backgroundColor: "rgba(231,76,60,0.1)", borderWidth: 2, pointRadius: 0, fill: true, tension: 0.1 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => "回撤: " + ctx.parsed.y.toFixed(2) + "%" } } },
            scales: {
                x: { display: true, ticks: { maxTicksLimit: 12, font: { size: 10 } } },
                y: { display: true, ticks: { callback: v => v + "%", font: { size: 10 } } },
            },
        },
    });
}

let _lastChartPeriod = null;

async function prefetchNavAll(code) {
    try {
        const resp = await API.get(`/api/funds/${code}/nav-history?period=all`);
        state.navHistoryAll = resp.data || [];
    } catch (err) {
        state.navHistoryAll = [];
    }
}

function filterNavByPeriod(allNav, period) {
    if (period === 'all' || !allNav.length) return allNav;
    const d = new Date();
    let cutoff;
    if (period === '1y') { d.setFullYear(d.getFullYear() - 1); cutoff = d.toISOString().slice(0, 10); }
    else if (period === '3y') { d.setFullYear(d.getFullYear() - 3); cutoff = d.toISOString().slice(0, 10); }
    else if (period === '5y') { d.setFullYear(d.getFullYear() - 5); cutoff = d.toISOString().slice(0, 10); }
    else if (period === 'ytd') { cutoff = `${d.getFullYear()}-01-01`; }
    if (!cutoff) return allNav;
    return allNav.filter(item => item.nav_date >= cutoff);
}

async function loadCharts(force = false) {
    if (!state.fund) return;
    const period = state.activePeriod === "all" ? "all" : state.activePeriod;
    // Filter from cached full NAV history
    if (state.navHistoryAll.length > 0) {
        state.navHistory = filterNavByPeriod(state.navHistoryAll, period);
        _lastChartPeriod = period;
        buildNavChart(state.navHistory);
        buildDrawdownChart(state.navHistory);
        return;
    }
    // Fallback: fetch from API if prefetch hasn't completed
    if (!force && _lastChartPeriod === period && state.navHistory.length > 0) {
        buildNavChart(state.navHistory);
        buildDrawdownChart(state.navHistory);
        return;
    }
    try {
        const resp = await API.get(`/api/funds/${state.fund.code}/nav-history?period=${period}`);
        state.navHistory = resp.data;
        _lastChartPeriod = period;
        buildNavChart(state.navHistory);
        buildDrawdownChart(state.navHistory);
    } catch (err) {
        console.error("Chart load error:", err);
    }
}

async function loadDca(code) {
    try {
        const dcaResp = await API.get(`/api/funds/${code}/dca?amount=1000&years=3`);
        state.dca = dcaResp;
        // If DCA section doesn't exist yet, render to create it; otherwise update quietly
        if (state.dca && document.getElementById('dcaChart')) {
            buildDcaChart();
        } else if (state.dca) {
            render();
        }
    } catch (err) {
        state.dca = null;
    }
}

async function refresh() {
    if (!state.fund) return;
    const period = state.activePeriod === 'all' ? 'all' : state.activePeriod;
    // Update period tab buttons immediately
    document.querySelectorAll('.period-tabs button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === state.activePeriod);
    });

    // Update chart from cached NAV data (instant, no network)
    state.navHistory = filterNavByPeriod(state.navHistoryAll, period);
    _lastChartPeriod = period;
    buildNavChart(state.navHistory);
    buildDrawdownChart(state.navHistory);

    // Fetch fresh metrics from backend (only this, not nav-history)
    try {
        const metricsPeriod = state.activePeriod === 'all' ? 'all' : state.activePeriod;
        const metricsResp = await API.get(`/api/funds/${state.fund.code}/metrics?period=${metricsPeriod}`);
        state.metrics = metricsResp.metrics;
        // Update metric cards inline — no full re-render needed
        updateMetricCards();
    } catch (err) {
        console.error('Refresh error:', err);
    }
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------
async function onSearchInput() {
    const q = state.searchQuery.trim();
    if (q.length < 1) { state.searchResults = []; updateSearchDropdown(); return; }
    if (state.searchTimer) clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(async () => {
        try {
            const results = await API.search(q);
            state.searchResults = results || [];
        } catch { state.searchResults = []; }
        updateSearchDropdown();
    }, 300);
}

// Lightweight dropdown update without full re-render
function updateSearchDropdown() {
    const dd = document.getElementById('searchDropdown');
    if (!dd) return;
    dd.style.display = state.searchResults.length ? 'block' : 'none';
    dd.innerHTML = state.searchResults.map(r =>
        `<div class="search-item" data-code="${r.code}">
            <span class="fund-code">${r.code}</span>
            <span class="fund-name">${esc(r.name)}</span>
        </div>`
    ).join('');
    // Re-bind only search item clicks
    dd.querySelectorAll('.search-item').forEach(el => {
        el.addEventListener('click', () => selectFund(el.dataset.code));
    });
}

function selectFund(code) {
    state.searchResults = [];
    state.activePeriod = "1y";
    loadFund(code);
}

// ---------------------------------------------------------------------------
// Valuation gauge helper (PE-based, not NAV)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// DCA chart
// ---------------------------------------------------------------------------

function buildDcaChart() {
    const ctx = document.getElementById('dcaChart');
    if (!ctx || !state.dca || !state.dca.monthly) return;
    if (state.dcaChart) { state.dcaChart.destroy(); state.dcaChart = null; }

    const monthly = state.dca.monthly;
    const labels = monthly.map(m => m.date);
    const nav = monthly.map(m => m.nav);
    const value = monthly.map(m => m.value / 10000); // portfolio value in wan
    const invested = monthly.map(m => m.cumulative_invested / 10000); // cumulative invested in wan
    const costBasis = monthly.map(m => m.cost_basis);

    state.dcaChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: '累计投入(万)', data: invested, borderColor: '#999', borderWidth: 1.5, borderDash: [2,2], pointRadius: 0, fill: false, tension: 0.1, yAxisID: 'y' },
                { label: '持仓市值(万)', data: value, borderColor: '#4a90d9', backgroundColor: 'rgba(74,144,217,0.08)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.1, yAxisID: 'y' },
                { label: '平均成本', data: costBasis, borderColor: '#f39c12', borderWidth: 2, borderDash: [5,5], pointRadius: 0, fill: false, tension: 0.1, yAxisID: 'y' },
                { label: '基金净值', data: nav, borderColor: '#27ae60', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, yAxisID: 'y' },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 8, padding: 16, font: { size: 11 } } },
                tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(4) } },
            },
            scales: {
                x: { display: true, ticks: { maxTicksLimit: 12, font: { size: 10 } } },
                y: { display: true, position: 'left', ticks: { font: { size: 10 } } },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// DCA Interpretation
// ---------------------------------------------------------------------------

function renderDcaInterpretation(dca) {
    if (!dca || !dca.monthly) return '';
    const d = dca, m = d.monthly;

    // Find key points
    let maxUnderwater = { depth: 0, date: '' };
    for (let i = 0; i < m.length; i++) {
        const diff = (m[i].cost_basis - m[i].nav) / m[i].nav * 100;
        if (diff > maxUnderwater.depth) {
            maxUnderwater = { depth: diff, date: m[i].date };
        }
    }

    const dcaWins = d.total_return_pct > d.lump_sum.return_pct;
    const monthsUnderwater = m.filter(x => x.nav < x.cost_basis).length;
    const underPct = monthsUnderwater / m.length * 100;

    let interpretation = '';

    // Overall comparison (descriptive only, no recommendations)
    if (dcaWins) {
        interpretation += `<p><strong>定投收益高于一次性</strong>：定投收益率 ${d.total_return_pct > 0 ? '+' : ''}${d.total_return_pct.toFixed(1)}%，一次性 ${d.lump_sum.return_pct > 0 ? '+' : ''}${d.lump_sum.return_pct.toFixed(1)}%。在该时段内市场整体走低或震荡，定投通过分批买入分摊了成本。</p>`;
    } else {
        interpretation += `<p><strong>一次性收益高于定投</strong>：一次性 ${d.lump_sum.return_pct > 0 ? '+' : ''}${d.lump_sum.return_pct.toFixed(1)}%，定投 ${d.total_return_pct > 0 ? '+' : ''}${d.total_return_pct.toFixed(1)}%。市场整体走高时，前期买入成本更低。定投是对不确定性的对策——没有人事先知道哪种方式结果更好。</p>`;
    }

    // Underwater analysis (descriptive only)
    if (underPct > 30) {
        interpretation += `<p><strong>波动较大</strong>：在 ${m.length} 个月的定投周期中，有 ${monthsUnderwater} 个月（${underPct.toFixed(0)}%）净值低于持仓成本，即大部分时间处于浮亏状态。${
            maxUnderwater.depth > 0 ? `最深时净值比成本低 ${maxUnderwater.depth.toFixed(1)}%（${maxUnderwater.date}）。` : ''
        } 这是定投过程中可能遇到的情况——市场下跌时成本也在下降。</p>`;
    } else if (underPct > 10) {
        interpretation += `<p><strong>波动适中</strong>：约 ${underPct.toFixed(0)}% 的时间净值低于成本。浮亏期间定投以更低价格获取份额，是定投机制的一部分。</p>`;
    } else {
        interpretation += `<p><strong>多数时间盈利</strong>：仅 ${underPct.toFixed(0)}% 的时间净值低于成本。该基金在此期间整体呈上升趋势。</p>`;
    }

    // Cost-navigation gap (descriptive only)
    const finalGap = ((d.avg_cost_per_share - d.current_nav) / d.current_nav * 100).toFixed(1);
    if (d.current_nav > d.avg_cost_per_share) {
        interpretation += `<p><strong>成本与净值</strong>：最终净值 ${d.current_nav.toFixed(4)}，平均成本 ${d.avg_cost_per_share.toFixed(4)}，净值高于成本约 ${Math.abs(finalGap)}%。</p>`;
    } else {
        interpretation += `<p><strong>成本与净值</strong>：当前净值 ${d.current_nav.toFixed(4)}，平均成本 ${d.avg_cost_per_share.toFixed(4)}，净值低于成本约 ${Math.abs(finalGap)}%。</p>`;
    }

    return `<div class="dca-interpretation">${interpretation}</div>`;
}

// ---------------------------------------------------------------------------
// Lightweight metric-card update (no full re-render)
// ---------------------------------------------------------------------------

function updateMetricCards() {
    const cards = document.querySelectorAll('.metric-cards .card');
    if (!cards.length) return;

    const c = computed();
    const period = state.activePeriod === 'all' ? 'since_inception' : state.activePeriod;

    // Map card data-metric attribute to computed value + formatter
    const cardMap = {
        annual_return: { value: c.metricReturn, fmt: formatPct, cls: v => v >= 0 ? 'positive' : 'negative' },
        max_drawdown: { value: c.metricDrawdown, fmt: formatPct, cls: () => 'negative' },
        volatility: { value: c.metricVol, fmt: formatPct, cls: v => (v || 0) > 0.25 ? 'negative' : '' },
        sharpe: { value: c.metricSharpe, fmt: formatNum, cls: () => '' },
        calmar: { value: c.metricCalmar, fmt: formatNum, cls: () => '' },
        win_rate: { value: c.metricWinRate, fmt: formatPct, cls: () => '' },
    };

    cards.forEach(card => {
        const key = card.dataset.metric;
        const info = cardMap[key];
        if (!info) return;

        const valEl = card.querySelector('.card-value');
        if (!valEl) return;

        // Update value
        valEl.textContent = info.fmt(info.value);
        valEl.className = 'card-value ' + (info.cls(info.value) || '');

        // Update period label in card-title
        const label = card.querySelector('.card-label');
        if (label && state.activePeriod) {
            // Replace period suffix in label text
            label.childNodes[0].textContent = label.childNodes[0].textContent.replace(/\(.*?\)/, '(' + state.activePeriod + ')');
        }
    });

    // Update max drawdown date range
    const mddInfo = state.metrics?.max_drawdown?.[period] || null;
    const subEl = document.querySelector('.highlight-red .card-sub');
    if (subEl && mddInfo?.peak_date) {
        subEl.textContent = mddInfo.peak_date + ' \u2192 ' + mddInfo.trough_date;
    }
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------
function render() {
    const c = computed();

    // Search input
    const si = document.getElementById('searchInput');
    if (si) si.value = state.searchQuery;

    // Search dropdown
    updateSearchDropdown();

    // Period tabs
    const pt = document.getElementById("periodTabs");
    if (state.fund) {
        pt.innerHTML = [
            { v: "1y", l: "近1年" }, { v: "3y", l: "近3年" }, { v: "5y", l: "近5年" }, { v: "all", l: "成立以来" },
        ].map(p => `<button class="${state.activePeriod===p.v?'active':''}" data-period="${p.v}">${p.l}</button>`).join("");
    } else {
        pt.innerHTML = "";
    }

    // Loading
    document.getElementById("loading").style.display = state.loading ? "flex" : "none";

    // Main content
    const mc = document.getElementById("mainContent");
    if (state.loading) {
        mc.innerHTML = "";
        rebindEvents();
        return;
    }
    if (!state.fund) {
        mc.innerHTML = `
            <div class="landing">
                <div class="landing-hero">
                    <h2 class="landing-title">基金多维度分析平台</h2>
                    <p class="landing-desc">一站式基金数据分析工具，输入基金代码或名称即可查看年化收益、最大回撤、夏普比率、PE 估值、定投回测等多维度指标，助你做出更明智的投资决策。</p>
                </div>
            </div>`;
        rebindEvents();
        return;
    }

    const f = state.fund, ds = state.dataSummary, period = state.activePeriod === "all" ? "since_inception" : state.activePeriod;
    const isReturnPositive = c.metricReturn != null && c.metricReturn >= 0;
    const mddInfo = state.metrics?.max_drawdown?.[period] || null;
    const showPE = c.peRatio != null;
    const hasHoldings = state.holdings.length > 0;

    mc.innerHTML = `
        <div class="fund-info-bar">
            <h2>${esc(f.name)} <code>${esc(f.code)}</code></h2>
            <span class="badge">${esc(f.fund_type)}</span>
            ${ds ? `<span class="text-muted">NAV: ${ds.nav_start} ~ ${ds.nav_end} (${ds.nav_records}条)</span>` : ""}
        </div>
        <div class="metric-cards">
            <div class="card clickable" data-metric="annual_return">
                <div class="card-label">年化收益 (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value ${isReturnPositive?'positive':'negative'}">${formatPct(c.metricReturn)}</div>
            </div>
            <div class="card highlight-red clickable" data-metric="max_drawdown">
                <div class="card-label">最大回撤 (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value negative">${formatPct(c.metricDrawdown)}</div>
                ${mddInfo?.peak_date ? `<div class="card-sub">${mddInfo.peak_date} → ${mddInfo.trough_date}</div>` : ""}
            </div>
            <div class="card clickable" data-metric="volatility">
                <div class="card-label">波动率 (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value ${(c.metricVol||0) > 0.25 ? 'negative' : ''}">${formatPct(c.metricVol)}</div>
            </div>
            <div class="card clickable" data-metric="sharpe">
                <div class="card-label">夏普比率 (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value">${formatNum(c.metricSharpe)}</div>
            </div>
            ${showPE ? `<div class="card clickable" data-metric="pe_ratio">
                <div class="card-label">PE 比率 <span class="info-icon">?</span></div>
                <div class="card-value">${formatNum(c.peRatio, 1)}</div>
            </div>` : ""}
            <div class="card clickable" data-metric="calmar">
                <div class="card-label">Calmar (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value">${formatNum(c.metricCalmar)}</div>
            </div>
            <div class="card clickable" data-metric="win_rate">
                <div class="card-label">胜率 (${state.activePeriod}) <span class="info-icon">?</span></div>
                <div class="card-value">${formatPct(c.metricWinRate)}</div>
            </div>
        </div>
        <div class="charts-row">
            <div class="chart-card"><h3 data-metric="nav_chart" class="clickable">净值走势 <span class="info-icon">?</span></h3><canvas id="navChart"></canvas></div>
            <div class="chart-card"><h3 data-metric="drawdown_chart" class="clickable">回撤曲线 <span class="info-icon">?</span></h3><canvas id="drawdownChart"></canvas></div>
        </div>
        ${state.dca ? `<div class="section"><h3>定投回测 (月投\u00a5${state.dca.monthly_amount}, 近${state.dca.years}年)</h3>
            ${renderDcaInterpretation(state.dca)}
            <div class="dca-summary">
                <div class="dca-stat">
                    <div class="dca-label">定投总投入</div>
                    <div class="dca-value">\u00a5${(state.dca.total_invested/10000).toFixed(2)}万</div>
                </div>
                <div class="dca-stat">
                    <div class="dca-label">定投终值</div>
                    <div class="dca-value">\u00a5${(state.dca.final_value/10000).toFixed(2)}万</div>
                </div>
                <div class="dca-stat">
                    <div class="dca-label">定投收益率</div>
                    <div class="dca-value">${state.dca.total_return_pct>0?'+':''}${state.dca.total_return_pct.toFixed(1)}%</div>
                </div>
                <div class="dca-stat">
                    <div class="dca-label">一次性买入</div>
                    <div class="dca-value">${state.dca.lump_sum.return_pct>0?'+':''}${state.dca.lump_sum.return_pct.toFixed(1)}%</div>
                </div>
                <div class="dca-stat">
                    <div class="dca-label">平均成本</div>
                    <div class="dca-value">${state.dca.avg_cost_per_share.toFixed(4)}</div>
                </div>
                <div class="dca-stat">
                    <div class="dca-label">当前净值</div>
                    <div class="dca-value">${state.dca.current_nav.toFixed(4)}</div>
                </div>
            </div>
            <div class="chart-card" style="margin-top:12px;"><canvas id="dcaChart"></canvas><p class="dca-disclaimer">历史模拟不代表未来收益</p></div>
        </div>` : ''}
        ${hasHoldings ? `<div class="section"><h3>前十大持仓</h3>
            <table class="holdings-table">
                <thead><tr><th>股票代码</th><th>股票名称</th><th>占净值比例</th><th>报告日期</th></tr></thead>
                <tbody>${state.holdings.map(h => `
                    <tr><td><code>${esc(h.stock_code)}</code></td><td>${esc(h.stock_name)}</td><td>${h.weight}%</td><td>${h.report_date}</td></tr>
                `).join("")}</tbody>
            </table>
        </div>` : ""}
    `;

    rebindEvents();
    loadCharts();
    if (state.dca) buildDcaChart();
}

function computed() {
    if (!state.metrics) return {};
    const period = state.activePeriod === "all" ? "since_inception" : state.activePeriod;
    return {
        metricReturn: state.metrics.returns?.[period] ?? null,
        metricVol: state.metrics.volatility?.[state.activePeriod] ?? null,
        metricSharpe: state.metrics.sharpe?.[state.activePeriod] ?? null,
        metricDrawdown: state.metrics.max_drawdown?.[period]?.mdd ?? null,
        peRatio: state.metrics.pe_ratio?.pe ?? null,
        metricCalmar: state.metrics.calmar?.[state.activePeriod] ?? null,
        metricWinRate: state.metrics.win_rate?.[state.activePeriod] ?? null,
    };
}

function rebindEvents() {
    // Search input
    const si = document.getElementById("searchInput");
    if (si) {
        si.addEventListener("input", () => {
            state.searchQuery = si.value;
            onSearchInput();
        });
        si.addEventListener("keydown", e => { if (e.key === "Enter") selectFund(si.value.trim()); });
    }
    // Search dropdown
    document.querySelectorAll(".search-item").forEach(el => {
        el.addEventListener("click", () => selectFund(el.dataset.code));
    });
    // Period tabs
    document.querySelectorAll(".period-tabs button").forEach(btn => {
        btn.addEventListener("click", () => {
            state.activePeriod = btn.dataset.period;
            refresh();
        });
    });
    // Metric cards (click for info)
    document.querySelectorAll(".card.clickable").forEach(card => {
        card.addEventListener("click", () => openMetricInfo(card.dataset.metric));
    });
    // Chart title clicks → open metric info
    document.querySelectorAll("h3[data-metric].clickable").forEach(el => {
        el.addEventListener("click", () => openMetricInfo(el.dataset.metric));
    });
    // Header title → back to landing
    const h1 = document.querySelector('.header h1');
    if (h1) {
        h1.addEventListener('click', () => {
            state.fund = null;
            state.dataSummary = null;
            state.metrics = null;
            state.holdings = [];
            state.peHistory = null;
            state.navHistory = [];
            state.navHistoryAll = [];
            state.dcaResult = null;
            state.searchQuery = "";
            state.searchResults = [];
            // Clear search input visually
            const si = document.getElementById('searchInput');
            if (si) si.value = '';
            render();
        });
    }
    // Click outside search → close dropdown
    document.addEventListener('click', (e) => {
        const dd = document.getElementById('searchDropdown');
        const si = document.getElementById('searchInput');
        if (dd && si && !si.contains(e.target) && !dd.contains(e.target)) {
            dd.style.display = 'none';
        }
    });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => render());
