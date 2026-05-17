# 基金多维度分析平台

## 1. 项目概览

全市场公募基金分析平台，支持任意基金代码的搜索、净值走势、风险指标计算、PE 估值、定投回测。双端覆盖：Web SPA + 微信小程序。

## 2. 技术栈

| 层 | Web 版 | 小程序版 |
|---|---|---|
| 后端 | Python 3 + FastAPI + uvicorn | 同左 (gunicorn + uvicorn worker) |
| ORM | SQLAlchemy 2.x + SQLite（`backend/data.db`） | SQLAlchemy 2.x + MySQL（CloudBase 云托管） |
| HTTP | httpx（爬虫层请求东方财富 API） | 同左 |
| HTML 解析 | BeautifulSoup4（持仓表格解析） | 同左 |
| 前端 | Vanilla JS + Chart.js 4.4（CDN），零框架 SPA | WXML/WXSS/JS（零框架） |
| 部署 | 单进程 `python main.py` → `0.0.0.0:8000` | Docker + CloudBase 云托管 → `0.0.0.0:80` |

依赖清单（`backend/requirements.txt`）：`fastapi`, `uvicorn`, `httpx`, `beautifulsoup4`, `apscheduler`, `sqlalchemy`, `pymysql`

Docker 镜像额外安装：`gunicorn`

## 3. 项目结构

```
D:\guzhi\
├── CLAUDE.md
├── README.md
├── Dockerfile                    # CloudBase 云托管部署 (Alpine + gunicorn)
├── .dockerignore
├── test_perf.sh                  # 云托管性能测试脚本
└── backend/
    ├── main.py                   # FastAPI 应用 + 全部 API 路由 + 3 层缓存
    ├── models.py                 # ORM 模型：Fund, Holding, NavEstimate, FundNav
    ├── database.py               # SQLite/MySQL 双引擎 + Session 管理 + 自动建库
    ├── config.py                 # 全局配置常量（API URL, DB 路径）
    ├── requirements.txt
    ├── data.db                   # SQLite 数据库文件（本地运行时生成）
    ├── calculator/
    │   ├── __init__.py
    │   ├── metrics.py            # 全部指标计算 + PE + DCA 回测
    │   └── commentary.py         # 投资大师点评
    ├── scraper/
    │   ├── __init__.py
    │   ├── fund_list.py          # 基金列表爬取（rankhandler API）
    │   ├── fund_nav.py           # 净值历史爬取（pingzhongdata API）
    │   ├── fund_holdings.py      # 前十大持仓爬取（FundArchivesDatas API）
    │   ├── test_fund_list.py
    │   └── test_fund_holdings.py
    └── static/
        ├── index.html            # SPA HTML 骨架
        ├── app.js                # 前端全部业务逻辑
        └── style.css             # 全部样式（响应式）
```

## 4. 数据流

```
东方财富 API (3 个数据源)
  ├─ rankhandler.aspx ──────→ fund_list.py ──────→ Fund 表
  ├─ pingzhongdata/{code}.js → fund_nav.py ───────→ FundNav 表
  └─ FundArchivesDatas.aspx ─→ fund_holdings.py ──→ Holding 表
                                    │
                     SQLite / MySQL (data.db or fund_db)
                                    │
                    FastAPI (main.py) — 4 层缓存
                                    │
            ┌───────────────────────┼────────────────────────┐
            │                       │                        │
    浏览器 SPA                 微信小程序                curl/health
    Vanilla JS + Chart.js     wx.cloud.callContainer
```

## 5. 启动流程

```
容器/进程启动
  ├── database.py 模块级代码:
  │   ├── SQLite: 创建引擎 (check_same_thread=False)
  │   └── MySQL: 连接 base URL → CREATE DATABASE IF NOT EXISTS
  │              → 创建连接池 (pool_size=5, pool_pre_ping=True)
  │              → 验证连接 (SELECT 1)
  │        失败则 sys.exit(1) → 容器重启
  │
  ├── lifespan():
  │   ├── init_db() → Base.metadata.create_all()
  │   ├── 后台线程: fetch_fund_list("all") → save_to_db(10000条, batch=500)
  │   │   └── 写入 MySQL funds 表（upsert by code）
  │   └── yield → "Fund Analyzer ready"
  │
  └── HTTP 服务就绪 (health check 立即可用)
```

## 6. 缓存策略（4 层）

| 缓存 | 位置 | TTL | 作用 |
|---|---|---|---|
| Fund list 内存缓存 | `_fund_list_cache` | 1小时 | 搜索兜底，名称模糊匹配 |
| Fund list DB 持久化 | MySQL `funds` 表 | 永久 | 搜索主路径，启动时预加载 |
| Fund detail 缓存 | `_detail_cache` | 当天 | 指标+持仓计算结果，当天不重算 |
| DCA 缓存 | `_dca_cache` | 当天 | 定投回测，同参数当天不重算 |
| PE 缓存 | `_pe_cache` (metrics.py) | 5分钟 | 持仓 PE 数据 |

## 7. 关键文件与函数

### `backend/main.py` — FastAPI 入口

**生命周期**：`lifespan()` 启动时建表 + 后台预加载全市场基金列表到 DB。

**缓存变量**：
- `_fund_list_cache` — 全市场基金列表内存缓存（1h TTL）
- `_detail_cache` — 基金详情当天缓存（key=`code`）
- `_dca_cache` — DCA 回测当天缓存（key=`code:amount:years`）

**路由处理函数（共 10 个）**：

| 函数 | 路由 | 功能 |
|---|---|---|
| `serve_dashboard()` | `GET /` | 返回 `index.html` |
| `health_check()` | `GET /health` | 健康检查 + 数据库连通性验证 |
| `list_funds(db)` | `GET /api/funds` | 列出所有基金 |
| `search_fund(q, db)` | `GET /api/funds/search` | 三级搜索（DB → 内存缓存 → pingzhongdata 兜底） |
| `fund_detail(code, db)` | `GET /api/funds/{code}` | 基金详情 + 自动发现 |
| `fund_nav_history(code, period, db)` | `GET /api/funds/{code}/nav-history` | 净值历史（period: 1y/3y/5y/ytd/all） |
| `fund_metrics(code, period, db)` | `GET /api/funds/{code}/metrics` | 指标计算（含 PE） |
| `fund_holdings(code, db)` | `GET /api/funds/{code}/holdings` | 前十大持仓 |
| `fund_dca(code, amount, years, db)` | `GET /api/funds/{code}/dca` | 月定投回测 |
| `fund_commentary(code, db)` | `GET /api/funds/{code}/commentary` | 投资大师点评 |

**搜索逻辑**（`search_fund` 内的三级策略）：
1. 查本地 DB（启动时已预加载 ~10000 条，几乎总能命中）
2. 查内存缓存 `_cached_fund_list()`（1h TTL，名称模糊匹配）
3. pingzhongdata 兜底：6 位纯数字且前两步未命中时，`fetch_fund_name(q)` 查名称 → `save_to_db` 入库

**自动发现**（`fund_detail` 内）：找不到基金时从内存缓存查找 → pingzhongdata 兜底 → `save_to_db` 入库。

### `backend/models.py` — ORM 模型

| 类 | 表名 | 关键字段 | 索引/约束 |
|---|---|---|---|
| `Fund` | `funds` | `id`, `code`(unique), `name`, `fund_type`(default=`"OTHER"`), `tracking_index`, `scale` | `ix_funds_code` on `code` |
| `Holding` | `holdings` | `id`, `fund_id`(FK→funds.id), `stock_code`, `stock_name`, `weight`, `report_date` | upsert by `(fund_id, stock_code, report_date)` |
| `NavEstimate` | `nav_estimates` | `id`, `fund_id`(FK), `official_nav`, `estimated_nav`, `nav_date`, `realtime_nav` | 预留表，当前未使用 |
| `FundNav` | `fund_nav` | `id`, `fund_id`(FK), `nav_date`, `unit_nav`, `cumulative_nav`, `daily_return` | `ix_fund_nav_fund_date(fund_id, nav_date)` |

`daily_return` 在 `save_nav_to_db()` 中预计算：`(unit_nav_t / unit_nav_{t-1}) - 1`。

### `backend/database.py` — 数据库连接

```python
# SQLite:
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# MySQL (检测 URL 前缀自动切换):
# 1. 连接 base URL → CREATE DATABASE IF NOT EXISTS (utf8mb4)
# 2. 创建连接池: pool_size=5, pool_recycle=300, pool_pre_ping=True
# 3. 验证连接: SELECT 1
# 失败 → sys.exit(1) → 容器重启

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
get_db()  # FastAPI Depends 注入
init_db()  # Base.metadata.create_all()
```

### `backend/config.py` — 配置常量

| 常量 | 值 |
|---|---|
| `DATABASE_URL` | 环境变量 `DATABASE_URL` 或默认 `sqlite:///{BASE_DIR}/data.db` |
| `FUND_LIST_URL` | `fund.eastmoney.com/data/rankhandler.aspx` |
| `FUND_DETAIL_URL` | `fund.eastmoney.com/pingzhongdata/{fund_code}.js` |
| `FUND_HOLDINGS_URL` | `fundf10.eastmoney.com/FundArchivesDatas.aspx` |
| `STOCK_QUOTE_URL` | `push2.eastmoney.com/api/qt/ulist.np/get` |

### `backend/scraper/fund_list.py` — 基金列表爬虫

| 函数 | 职责 |
|---|---|
| `_parse_jsonp(text)` | 修复 non-standard JSON（unquoted JS keys）后解析 |
| `fetch_fund_list(fund_type="qdii")` | 拉取基金列表，最多 10000 条。`fund_type="all"` 获取全市场 |
| `filter_us_qdii(funds)` | 关键词过滤美股 QDII（已基本弃用） |
| `_guess_tracking_index(name)` | 根据名称推测跟踪指数（NASDAQ/S&P/Dow Jones） |
| `save_to_db(funds, batch_size=500)` | 分批 upsert 基金记录（每 500 条 commit），返回 (inserted, updated) |

### `backend/scraper/fund_nav.py` — 净值爬虫

| 函数 | 职责 |
|---|---|
| `fetch_fund_name(fund_code)` | 从 pingzhongdata JS 正则提取 `var fS_name`，排名 API 覆盖范围外的兜底 |
| `fetch_nav_history(fund_code)` | 解析 `Data_netWorthTrend`（单位净值）和 `Data_ACWorthTrend`（累计净值） |
| `save_nav_to_db(fund_id, nav_data)` | 合并 NAV 按日期，计算 daily_return，upsert by `(fund_id, nav_date)` |
| `_last_trading_day()` | 跳过周末返回最近交易日 |
| `ensure_nav_data(fund_code)` | 一站式 helper：检查 `max(nav_date) >= 最近交易日`，过期则重新拉取 |

### `backend/scraper/fund_holdings.py` — 持仓爬虫

| 函数 | 职责 |
|---|---|
| `_parse_js_response(text)` | 解析 JS 变量赋值响应 |
| `_unescape_js_string(s)` | JS 字符串反转义 |
| `_parse_html_table(html_content)` | BeautifulSoup 解析持仓表格 |
| `_extract_report_date(api_data, html_content)` | 从 year/month 字段或 HTML 中提取季报日期 |
| `fetch_holdings(fund_code)` | 返回 `(holdings, report_date)` 或 None（债券/货基无持仓） |
| `save_holdings_to_db(fund_id, holdings, report_date)` | Upsert by `(fund_id, stock_code, report_date)` |
| `batch_fetch_all()` | 遍历 DB 所有基金拉取持仓 |

### `backend/calculator/metrics.py` — 指标计算引擎

**公共指标函数**（均接受 `nav_list: list[dict]` + `period: str`）：

| 函数 | 公式 |
|---|---|
| `max_drawdown` | `min((nav - peak) / peak)` |
| `max_drawdown_recovery` | 从回撤谷底到净值回到前高的天数 |
| `annualized_return` | `(end/start)^(365/days) - 1` |
| `volatility` | `std(daily_returns) × √252` |
| `sharpe_ratio` | `(ann_ret - 0.025) / vol` |
| `sortino_ratio` | `(ann_ret - 0.025) / downside_dev` |
| `calmar_ratio` | `ann_ret / |mdd|` |
| `win_rate` | `positive_days / total_days` |

**聚合函数**：`all_returns`, `all_volatilities`, `all_sharpes` — 对多周期调用单体函数。

**`compute_all_metrics(nav_list) -> dict`** — 一键计算所有指标，返回嵌套 dict 含 returns / max_drawdown / recovery_days / volatility / sharpe / sortino / calmar / win_rate。

**PE 比率**：
- `fund_pe_ratio(fund_code)` — 持仓加权调和平均 PE，5 分钟内存缓存
- `_fetch_stock_pes(stocks)` — 并行拉取个股 PE TTM（ThreadPoolExecutor, max 10 workers），通过 Eastmoney push2 API
- `_market_prefix(code)` — 按股票代码推断市场前缀（上海=1, 深圳=0, 美股=106）

**定投回测**：
- `dca_backtest(nav_list, monthly_amount=1000, years=3)` — 月定投模拟 + 一次性买入对比，返回 monthly 明细 + lump_sum 对比

### 前端文件

**Web 版（`static/`）**：
- `index.html` — SPA 骨架，Chart.js 4.4 CDN
- `app.js` — 全部业务逻辑，`state` 全局状态对象，`API.get()`/`API.search()` fetch 封装，300ms 搜索防抖，全量 NAV 缓存 + 本地 period 过滤
- `style.css` — 响应式布局（768px 断点）

**小程序版（`miniprogram/`）**：
- `app.js` — 全局配置：`useCloud` 切换云托管/本地模式，`cloudEnv`/`cloudService` 云环境配置
- `utils/api.js` — API 封装：`useCloud=true` → `wx.cloud.callContainer()`，`useCloud=false` → `wx.request(localhost:8000)`，60s 超时
- `pages/index/index.js` — 主页面逻辑：基金搜索、8 项指标、DCA 回测、自选收藏、周期切换

## 8. API 端点

| 方法 | 路径 | Query 参数 | 返回格式 |
|---|---|---|---|
| GET | `/` | — | `index.html` |
| GET | `/health` | — | `{status, service, database}` |
| GET | `/api/funds` | — | `[{id, code, name, fund_type, tracking_index, scale}]` |
| GET | `/api/funds/search` | `q` (必填) | `{query, count, results: [{code, name, fund_type, source}]}` |
| GET | `/api/funds/{code}` | — | `{fund, metrics, holdings, data_summary}` |
| GET | `/api/funds/{code}/nav-history` | `period` (1y\|3y\|5y\|ytd\|all) | `{fund_code, period, count, data}` |
| GET | `/api/funds/{code}/metrics` | `period` (1y\|3y\|5y\|all) | `{fund_code, fund_name, metrics}` |
| GET | `/api/funds/{code}/holdings` | — | `[{stock_code, stock_name, weight, report_date}]` |
| GET | `/api/funds/{code}/dca` | `amount` (≥100), `years` (1-10) | `{monthly_amount, years, total_invested, final_value, ...}` |
| GET | `/api/funds/{code}/commentary` | — | `{fund_code, fund_name, fund_type, commentary}` |

**关键约定**：
- `/api/funds/search` **永远不返回 404**
- 非搜索端点找不到基金返回 HTTP 404
- `fund_type` 默认值 `"OTHER"`
- `/health` 含 `database: "connected"|"disconnected"` 字段
- period 参数有 FastAPI regex 校验

## 9. 数据库 Schema

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

MySQL 上额外使用 `utf8mb4` 字符集和 `ix_holdings_fund_stock_date` 索引。

## 10. 开发规范

### 命名
- Python `snake_case` 函数/变量，`UPPER_CASE` 常量，`CamelCase` 类，`_` 前缀私有
- JS `camelCase` 函数/变量，`UPPER_CASE` 常量，状态集中放在 `state` 对象

### 类型注解
- Python 所有函数参数和返回值必须有类型注解
- 使用 `Optional[type]`

### 数据库
- 本地 SQLite，云端 MySQL（通过 `DATABASE_URL` 环境变量自动切换）
- MySQL 下启动时自动 `CREATE DATABASE IF NOT EXISTS`
- 写操作 try/except 包裹，失败 rollback

### API 端点
- 搜索接口永不返回 404
- 列表类端点直接返回列表 `[{...}]`，非包装对象
- period 参数使用 FastAPI `Query(pattern=...)` regex 校验

### 错误处理
- 对外接口 try/except 兜底，返回 HTTP 错误（404/502）
- 内部函数直接 raise
- 爬虫层网络错误返回 None 或空列表，不 crash
- MySQL 连接失败 → `sys.exit(1)` → 容器自动重启
- 基金列表预热失败 → 日志 warning，不影响启动

### 前端性能
- Web 端 NAV 全量缓存 `navHistoryAll`，period 切换本地过滤不请求网络
- Period 切换仅重新请求 `/api/funds/{code}/metrics`
- DCA 后台异步加载，不阻塞首屏
- 搜索 300ms 防抖

## 11. Code Review 检查清单

- [ ] 无 QDII 硬编码（`fund_type` 默认 `"OTHER"`，搜索用 `"all"`）
- [ ] 默认值正确（models 中 `fund_type` default=`"OTHER"`）
- [ ] 无重复东方财富 API 调用（PE 5min 缓存、NAV freshness 检查、持有基金列表预加载到 DB）
- [ ] 新查询模式有对应数据库索引
- [ ] 前端 period 切换不重复请求 NAV（`navHistoryAll` 本地过滤）
- [ ] 搜索覆盖全市场（`fetch_fund_list("all")` 预加载 + pingzhongdata 兜底）
- [ ] API 返回字段名与前端期望一致
- [ ] 云托管部署有启动日志（容器日志可见启动进度）

## 12. 部署

### 本地开发
```bash
cd backend && python main.py  # uvicorn → 0.0.0.0:8000
```

### 云端部署
```bash
# Dockerfile: python:3.11-alpine + gunicorn (1 worker, uvicorn worker)
# 端口: 80
# 时区: Asia/Shanghai
# 环境变量: DATABASE_URL=mysql+pymysql://user:pass@host:3306/fund_db
```

CloudBase 云托管构建流程：
1. 检出代码 → 2. Docker 构建（含 C 编译工具链，装完即删） → 3. 镜像推送到 TCR → 4. EKS 虚拟服务部署

## 13. 已知边界

- rankhandler API 仅返回排名前 10000 的基金 → 启动预加载覆盖此范围，pingzhongdata 兜底覆盖 6 位精确代码
- PE 数据：美股 ticker-market 映射不可靠（默认 `106` NASDAQ 前缀），部分持仓可能缺失 PE，覆盖权重不足 50% 时返回 `pe: null`
- NAV freshness 基于 `_last_trading_day()`（跳过周末），不处理节假日
- 定投回测要求至少 12 个月数据，不足返回 null
- `apscheduler` 依赖已安装但调度器未启用
- `NavEstimate` 表预留未使用
- `ec-canvas` 组件目录未创建，小程序版未使用 ECharts

## 14. 启动

```bash
cd backend && python main.py
# → http://localhost:8000
```
