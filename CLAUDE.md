# 基金多维度分析平台

## 1. 项目概览

全市场公募基金分析平台，支持任意基金代码的搜索、净值走势、风险指标计算、PE 估值、定投回测。Web SPA 浏览器打开即用。

## 2. 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3 + FastAPI + uvicorn |
| ORM | SQLAlchemy 2.x + SQLite（`backend/data.db`） |
| HTTP | httpx（爬虫层请求东方财富 API） |
| HTML 解析 | BeautifulSoup4（持仓表格解析） |
| 前端 | Vanilla JS + Chart.js 4.4（CDN），零框架 SPA |
| 部署 | 单进程 `python main.py` → `0.0.0.0:8000` |

依赖清单（`backend/requirements.txt`）：`fastapi`, `uvicorn`, `httpx`, `beautifulsoup4`, `apscheduler`, `sqlalchemy`

## 3. 项目结构

```
D:\guzhi\
├── CLAUDE.md
├── README.md
└── backend/
    ├── main.py               # FastAPI 应用 + 全部 API 路由
    ├── models.py             # ORM 模型：Fund, Holding, NavEstimate, FundNav
    ├── database.py           # SQLite 引擎 + Session 管理 + init_db()
    ├── config.py             # 全局配置常量（API URL, DB 路径）
    ├── requirements.txt      # Python 依赖
    ├── data.db               # SQLite 数据库文件（运行时生成）
    ├── calculator/
    │   ├── __init__.py
    │   ├── metrics.py        # 全部指标计算 + PE + DCA 回测
    │   └── commentary.py     # 投资大师点评（后端仅存，前端未使用）
    ├── scraper/
    │   ├── __init__.py
    │   ├── fund_list.py      # 基金列表爬取（rankhandler API）
    │   ├── fund_nav.py       # 净值历史爬取（pingzhongdata API）
    │   ├── fund_holdings.py  # 前十大持仓爬取（FundArchivesDatas API）
    │   ├── test_fund_list.py
    │   └── test_fund_holdings.py
    └── static/
        ├── index.html        # SPA HTML 骨架
        ├── app.js            # 前端全部业务逻辑（~790 行）
        └── style.css         # 全部样式（响应式）
```

## 4. 数据流

```
东方财富 API (3 个数据源)
  ├─ rankhandler.aspx ──────→ fund_list.py ──────→ Fund 表
  ├─ pingzhongdata/{code}.js → fund_nav.py ───────→ FundNav 表
  └─ FundArchivesDatas.aspx ─→ fund_holdings.py ──→ Holding 表
                                    │
                            SQLite (data.db)
                                    │
                            FastAPI (main.py)
                                    │
                    浏览器 SPA (Vanilla JS + Chart.js)
```

## 5. 关键文件与函数

### `backend/main.py` — FastAPI 入口（505 行）

**生命周期**：`lifespan()` 启动时调用 `init_db()` 建表。

**模块级状态**：`_holdings_fetch_attempted: set` — 每个进程生命周期内对无持仓基金只尝试一次爬取，避免重复请求。

**导入的核心函数**：
- `compute_all_metrics`, `fund_pe_ratio`, `dca_backtest` — 来自 `calculator.metrics`
- `ensure_nav_data` — 来自 `scraper.fund_nav`
- `fetch_holdings`, `save_holdings_to_db` — 来自 `scraper.fund_holdings`

**路由处理函数（共 10 个）**：

| 函数 | 路由 | 功能 |
|---|---|---|
| `serve_dashboard()` | `GET /` | 返回 `index.html` |
| `health_check()` | `GET /health` | 健康检查 |
| `list_funds(db)` | `GET /api/funds` | 列出所有基金 |
| `search_fund(q, db)` | `GET /api/funds/search` | 三级搜索（DB → rankhandler → pingzhongdata 兜底） |
| `fund_detail(code, db)` | `GET /api/funds/{code}` | 基金详情 + 自动发现 |
| `fund_nav_history(code, period, db)` | `GET /api/funds/{code}/nav-history` | 净值历史（period: 1y/3y/5y/ytd/all） |
| `fund_metrics(code, period, db)` | `GET /api/funds/{code}/metrics` | 指标计算（含 PE） |
| `fund_holdings(code, db)` | `GET /api/funds/{code}/holdings` | 前十大持仓 |
| `fund_dca(code, amount, years, db)` | `GET /api/funds/{code}/dca` | 月定投回测 |
| `fund_commentary(code, db)` | `GET /api/funds/{code}/commentary` | 投资大师点评（前端未接入） |

**搜索逻辑**（`search_fund` 内的三级策略）：
1. 查本地 DB：`Fund.code.contains(q) | Fund.name.contains(q)`
2. 查 Eastmoney rankhandler：`fetch_fund_list("all")` 取全市场 10000 条匹配
3. pingzhongdata 兜底：6 位纯数字且前两步未命中时，`fetch_fund_name(q)` 查名称

**自动发现**（`fund_detail` 内）：找不到基金时依次从 rankhandler → pingzhongdata 拉取，成功则自动 `save_to_db`。

### `backend/models.py` — ORM 模型（88 行）

| 类 | 表名 | 关键字段 | 索引/约束 |
|---|---|---|---|
| `Fund` | `funds` | `id`, `code`(unique), `name`, `fund_type`(default=`"OTHER"`), `tracking_index`, `scale` | `ix_funds_code` on `code` |
| `Holding` | `holdings` | `id`, `fund_id`(FK→funds.id), `stock_code`, `stock_name`, `weight`, `report_date` | upsert by `(fund_id, stock_code, report_date)` |
| `NavEstimate` | `nav_estimates` | `id`, `fund_id`(FK), `official_nav`, `estimated_nav`, `nav_date`, `realtime_nav` | 预留表，当前未使用 |
| `FundNav` | `fund_nav` | `id`, `fund_id`(FK), `nav_date`, `unit_nav`, `cumulative_nav`, `daily_return` | `ix_fund_nav_fund_date(fund_id, nav_date)` |

`daily_return` 在 `save_nav_to_db()` 中预计算：`(unit_nav_t / unit_nav_{t-1}) - 1`。

### `backend/database.py` — 数据库连接（25 行）

- `engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})`
- `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- `get_db()` — FastAPI Depends 注入，yield Session，finally close
- `init_db()` — `Base.metadata.create_all(bind=engine)`

### `backend/config.py` — 配置常量（19 行）

| 常量 | 值 |
|---|---|
| `DATABASE_URL` | `sqlite:///{BASE_DIR}/data.db` |
| `FUND_LIST_URL` | `fund.eastmoney.com/data/rankhandler.aspx` |
| `FUND_DETAIL_URL` | `fund.eastmoney.com/pingzhongdata/{fund_code}.js` |
| `FUND_HOLDINGS_URL` | `fundf10.eastmoney.com/FundArchivesDatas.aspx` |
| `STOCK_QUOTE_URL` | `push2.eastmoney.com/api/qt/ulist.np/get` |
| `NAV_SCRAPE_INTERVAL_MINUTES` | 30（预留，调度器未启用） |

### `backend/scraper/fund_list.py` — 基金列表爬虫（197 行）

| 函数 | 签名 | 职责 |
|---|---|---|
| `_parse_jsonp` | `(text: str) -> Optional[dict]` | 修复 rankhandler 的非标准 JSON（unquoted JS keys）后解析 |
| `fetch_fund_list` | `(fund_type: str = "qdii") -> list[dict]` | 拉取基金列表，最多 10000 条。`fund_type="all"` 获取全市场 |
| `filter_us_qdii` | `(funds: list[dict]) -> list[dict]` | 关键词过滤美股 QDII（已基本弃用，全市场搜索不默认 QDII） |
| `_guess_tracking_index` | `(name: str) -> str` | 根据基金名称推测跟踪指数（NASDAQ/S&P/Dow Jones） |
| `save_to_db` | `(funds: list[dict])` | Upsert 基金记录，按 `code` 去重 |

### `backend/scraper/fund_nav.py` — 净值爬虫（295 行）

| 函数 | 签名 | 职责 |
|---|---|---|
| `fetch_fund_name` | `(fund_code: str) -> Optional[str]` | 从 pingzhongdata JS 正则提取 `var fS_name`，排名 API 覆盖范围外的兜底 |
| `fetch_nav_history` | `(fund_code: str) -> Optional[dict]` | 解析 `Data_netWorthTrend`（单位净值）和 `Data_ACWorthTrend`（累计净值），返回 `{unit_nav, cumulative_nav}` |
| `save_nav_to_db` | `(fund_id: int, nav_data: dict) -> int` | 合并 NAV 按日期，计算 daily_return，upsert by `(fund_id, nav_date)` |
| `_last_trading_day` | `() -> date` | 跳过周末返回最近交易日 |
| `ensure_nav_data` | `(fund_code: str) -> int` | 一站式 helper：检查 `max(nav_date) >= 最近交易日`，过期则重新拉取 |

### `backend/scraper/fund_holdings.py` — 持仓爬虫（334 行）

| 函数 | 签名 | 职责 |
|---|---|---|
| `_parse_js_response` | `(text: str) -> Optional[dict]` | 解析 JS 变量赋值响应（unquoted keys + escaped strings） |
| `_unescape_js_string` | `(s: str) -> str` | JS 字符串反转义 |
| `_parse_html_table` | `(html_content: str) -> list[dict]` | BeautifulSoup 解析持仓表格 → `[{stock_code, stock_name, weight}]` |
| `_extract_report_date` | `(api_data: dict, html_content: str = "") -> date` | 从 year/month 字段或 HTML 中提取季报日期 |
| `_classify_stock` | `(stock_code: str) -> str` | 按代码首字符分类：字母→US, 数字→HK, 其他→OTHER（当前未被调用） |
| `fetch_holdings` | `(fund_code: str) -> Optional[tuple[list[dict], date]]` | 返回 `(holdings, report_date)` 或 None（债券/货基无持仓） |
| `save_holdings_to_db` | `(fund_id: int, holdings: list[dict], report_date: date) -> int` | Upsert by `(fund_id, stock_code, report_date)` |
| `batch_fetch_all` | `() -> dict` | 遍历 DB 所有基金拉取持仓，返回 summary |

### `backend/calculator/metrics.py` — 指标计算引擎（635 行）

**公共指标函数**（均接受 `nav_list: list[dict]` + `period: str`）：

| 函数 | 默认 period | 返回 | 公式 |
|---|---|---|---|
| `max_drawdown` | `"all"` | `{mdd, peak_date, trough_date}` | `min((nav - peak) / peak)` |
| `annualized_return` | `"all"` | `float` | `(end/start)^(365/days) - 1` |
| `volatility` | `"1y"` | `float` | `std(daily_returns) × √252` |
| `sharpe_ratio` | `"1y"` | `float` | `(ann_ret - 0.025) / vol` |
| `sortino_ratio` | `"1y"` | `float` | `(ann_ret - 0.025) / downside_dev` |
| `calmar_ratio` | `"3y"` | `float` | `ann_ret / |mdd|` |
| `win_rate` | `"1y"` | `float` | `positive_days / total_days` |

**聚合函数**：`all_returns`, `all_volatilities`, `all_sharpes` — 对多周期调用单体函数。

**`compute_all_metrics(nav_list) -> dict`** — 一键计算所有指标，返回嵌套 dict 含 returns / max_drawdown / volatility / sharpe / sortino / calmar / win_rate。

**PE 比率**：
- `fund_pe_ratio(fund_code) -> dict` — 持仓加权调和平均 PE，5 分钟内存缓存（`_pe_cache`）
- `_fetch_stock_pes(stocks) -> dict` — 并行拉取个股 PE TTM（ThreadPoolExecutor, max 10 workers），通过 Eastmoney push2 API
- `_market_prefix(code)` — 按股票代码推断市场前缀（上海=1, 深圳=0, 美股=106）
- `valuation_assessment(...)` — PE 估值区间评估（标记为 deprecated，主流程未调用）

**定投回测**：
- `dca_backtest(nav_list, monthly_amount=1000, years=3) -> dict` — 月定投模拟，含一次性买入对比，返回 monthly 明细 + lump_sum 对比

**辅助函数**：
- `_slice_by_period(nav_list, period)` — 按时间窗口截取 NAV 数据
- `_period_cutoff_date(period)` — 返回 SQL 查询用的 cutoff date（1y→365天前, 3y→1095天前, 5y→1825天前, ytd→今年1月1日, all→None）
- `_get_rf_rate()` — 无风险利率 2.5%

### `backend/calculator/commentary.py` — 投资大师点评（400 行，后端未删但前端未接入）

- `generate_commentary(fund_name, fund_type, metrics, holdings_count)` — 返回 6 位大师的点评 list
- 六个内部函数：`_buffett`, `_munger`, `_duan`, `_lynch`, `_bogle`, `_marks`
- `/api/funds/{code}/commentary` 端点仍存在但前端无对应 UI

### 前端文件

**`index.html`**（49 行）：
- 页面结构：header（标题 + 搜索 input + period tabs 容器）、loading 区、main content 区、metric info modal、disclaimer footer
- Chart.js 4.4 CDN 引入

**`app.js`**（792 行）：
- `METRIC_INFO` — 8 个指标的帮助文案对象（annual_return / max_drawdown / volatility / sharpe / pe_ratio / calmar / win_rate / nav_chart / drawdown_chart）
- `state` — 全局状态对象，含 `fund`, `metrics`, `holdings`, `navHistoryAll`（全量 NAV 缓存）, `activePeriod`, `searchResults`, `dca` 等
- `API` — fetch 封装：`API.get(url)`, `API.search(q)`
- **核心流程**：
  - `loadFund(code)` → 拉取 `fund_detail` → 后台启动 `prefetchNavAll` + `loadDca`
  - `refresh()` → period 切换：图表从 `navHistoryAll` 本地过滤（零网络），仅重新拉取 metrics → `updateMetricCards()` 轻量更新
  - `prefetchNavAll(code)` → 缓存全量 NAV 到 `navHistoryAll`
  - `filterNavByPeriod(allNav, period)` → 前端本地按 period 过滤
  - `onSearchInput()` → 300ms 防抖 → `/api/funds/search`
- **图表**：`buildNavChart`（双线：单位净值+累计净值）, `buildDrawdownChart`（回撤面积图）, `buildDcaChart`（四线：净值/成本/市值/投入）
- **渲染**：`render()` 全量 DOM 渲染，`updateMetricCards()` 轻量卡片更新
- **事件**：`rebindEvents()` — 搜索 input/keydown、search dropdown click、period tabs click、metric cards click（弹 modal）、header h1 click（回首页）、document click（关闭 dropdown）

**`style.css`**（216 行）：
- 响应式布局（768px 断点，charts-row 从 2列→1列，metric-cards 自适应列数）
- 颜色编码：`.positive`（绿 `#27ae60`）, `.negative`（红 `#e74c3c`）
- Modal 遮罩、DCA summary grid、holdings table、landing page hero

## 6. API 端点

| 方法 | 路径 | Query 参数 | 返回格式 |
|---|---|---|---|
| GET | `/` | — | `index.html` |
| GET | `/health` | — | `{status, service}` |
| GET | `/api/funds` | — | `[{id, code, name, fund_type, tracking_index, scale}]` |
| GET | `/api/funds/search` | `q` (必填, ≥1字符) | `{query, count, results: [{code, name, fund_type, source}]}` |
| GET | `/api/funds/{code}` | — | `{fund, metrics, holdings, data_summary}` |
| GET | `/api/funds/{code}/nav-history` | `period` (1y\|3y\|5y\|ytd\|all, default: all) | `{fund_code, period, count, data: [{nav_date, unit_nav, cumulative_nav, daily_return}]}` |
| GET | `/api/funds/{code}/metrics` | `period` (1y\|3y\|5y\|all, default: 1y) | `{fund_code, fund_name, metrics}` |
| GET | `/api/funds/{code}/holdings` | — | `[{stock_code, stock_name, weight, report_date}]` |
| GET | `/api/funds/{code}/dca` | `amount` (≥100, default 1000), `years` (1-10, default 3) | `{monthly_amount, years, total_invested, final_value, total_return_pct, annualized_return_pct, avg_cost_per_share, current_nav, lump_sum, monthly}` |

**关键约定**：
- `/api/funds/search` **永远不返回 404**，零结果返回 `{query, count: 0, results: []}`
- 非搜索端点找不到基金返回 HTTP 404
- `fund_type` 默认值 `"OTHER"`
- period 参数有 FastAPI regex 校验

## 7. 数据库 Schema

```sql
CREATE TABLE funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    fund_type VARCHAR(50) DEFAULT 'OTHER',
    tracking_index VARCHAR(100) DEFAULT '',
    scale FLOAT DEFAULT 0.0,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(id),
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) DEFAULT '',
    weight FLOAT DEFAULT 0.0,
    report_date DATE NOT NULL,
    created_at DATETIME
);

CREATE TABLE nav_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(id),
    official_nav FLOAT DEFAULT 0.0,
    estimated_nav FLOAT DEFAULT 0.0,
    nav_date DATE NOT NULL,
    realtime_nav FLOAT DEFAULT 0.0,
    last_stock_update DATETIME,
    created_at DATETIME
);

CREATE TABLE fund_nav (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL REFERENCES funds(id),
    nav_date DATE NOT NULL,
    unit_nav FLOAT DEFAULT 0.0,
    cumulative_nav FLOAT DEFAULT 0.0,
    daily_return FLOAT DEFAULT 0.0
);
CREATE INDEX ix_fund_nav_fund_date ON fund_nav(fund_id, nav_date);
```

- 所有级联：`cascade="all, delete-orphan"`（删除 Fund 时联动删除 Holding/NavEstimate/FundNav）
- `FundNav.daily_return` 在 `save_nav_to_db()` 中预计算
- `Holding` upsert 键：`(fund_id, stock_code, report_date)`
- `NavEstimate` 表预留，当前未使用

## 8. 开发规范

### 命名
- Python `snake_case` 函数/变量，`UPPER_CASE` 常量，`CamelCase` 类，`_` 前缀私有
- JS `camelCase` 函数/变量，`UPPER_CASE` 常量，状态集中放在 `state` 对象

### 类型注解
- Python 所有函数参数和返回值必须有类型注解
- 使用 `Optional[type]`（保持一致性）

### 数据库
- 模型变更后手动建索引（`create_all` 不更新已有表）
- 写操作 try/except 包裹，失败 rollback

### API 端点
- 搜索接口永不返回 404
- 列表类端点直接返回列表 `[{...}]`，非包装对象 `{items: [...]}`
- period 参数使用 FastAPI `Query(pattern=...)` regex 校验

### 错误处理
- 对外接口 try/except 兜底，返回 HTTP 错误（404/502）
- 内部函数直接 raise
- 爬虫层网络错误返回 None 或空列表，不 crash

### 前端性能
- NAV 全量缓存 `navHistoryAll`，period 切换本地过滤不请求网络
- Period 切换仅重新请求 `/api/funds/{code}/metrics`
- DCA 后台异步加载，不阻塞首屏
- 搜索 300ms 防抖

## 9. Code Review 检查清单

- [ ] 无 QDII 硬编码（`fund_type` 默认 `"OTHER"`，搜索用 `"all"`）
- [ ] 默认值正确（models 中 `fund_type` default=`"OTHER"`）
- [ ] 无重复东方财富 API 调用（PE 5min 缓存、NAV freshness 检查、holdings 每 session 单次尝试）
- [ ] 新查询模式有对应数据库索引
- [ ] 前端 period 切换不重复请求 NAV（`navHistoryAll` 本地过滤）
- [ ] 搜索覆盖全市场（`fetch_fund_list("all")` 非 `"qdii"`）
- [ ] 新增端点有 pingzhongdata 兜底（排名 API 仅 top 10000）
- [ ] API 返回字段名与前端期望一致

## 10. 已知边界

- rankhandler API 仅返回排名前 10000 的基金 → pingzhongdata 兜底仅限精确 6 位代码
- PE 数据：美股 ticker-market 映射不可靠（默认 `106` NASDAQ 前缀），部分持仓可能缺失 PE，覆盖权重不足 50% 时返回 `pe: null`
- NAV freshness 基于 `_last_trading_day()`（跳过周末），不处理节假日
- 定投回测要求至少 12 个月数据，不足返回 null
- `apscheduler` 依赖已安装但调度器未启用（config 中的 interval 常量预留）

## 11. 启动

```bash
cd D:\guzhi\backend
python main.py
# → http://localhost:8000
```
