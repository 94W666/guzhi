# 基金多维度分析平台

一站式基金数据分析工具，输入基金代码或名称即可查看年化收益、最大回撤、夏普比率、PE 估值、定投回测等多维度指标。

## 功能

- **基金搜索**：支持代码或名称搜索，自动从东方财富拉取全市场基金列表
- **7 项核心指标**：年化收益、最大回撤、波动率、夏普比率、PE 比率、Calmar 比率、胜率
- **周期切换**：1年 / 3年 / 5年 / 成立以来，图表即时切换（本地缓存，无网络请求）
- **净值走势图**：单位净值 + 累计净值双线 Chart.js 图表
- **回撤曲线**：从历史最高点算起的跌幅面积图
- **定投回测**：月定投模拟（默认 1000/月, 3年），含一次性买入对比 + 过程可视化
- **前十大持仓**：股票代码、名称、权重、季报日期
- **指标解读**：点击任意指标卡片弹出公式说明与评级标准
- **全市场支持**：不限于 QDII，任意公募基金代码均可使用

## 技术栈

| 层 | Web 版 | 小程序版 |
|---|---|---|
| 后端 | Python 3 + FastAPI + SQLAlchemy + SQLite | 同左 (CloudBase 云托管 + MySQL) |
| 前端 | Vanilla JS SPA + Chart.js 4.4 | WXML/WXSS/JS + ECharts ec-canvas |
| 数据源 | 东方财富公开 API | 同左 |

## 快速开始

```bash
pip install -r backend/requirements.txt
python backend/main.py
```

浏览器打开 http://localhost:8000

### 微信小程序版

1. 用微信开发者工具打开 `miniprogram/` 目录
2. 安装 ECharts：`cd miniprogram/utils && npm install echarts && cp node_modules/echarts/dist/echarts.min.js .`
3. 在开发者工具中勾选"不校验合法域名"
4. 启动后端 `python backend/main.py`，小程序即可调用本地 API
5. 上线时部署到 CloudBase 云托管：`Dockerfile` 已就绪

## 项目结构

```
├── Dockerfile                 # CloudBase 云托管部署
├── backend/                   # FastAPI 后端
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── config.py
│   ├── calculator/
│   │   └── metrics.py
│   ├── scraper/
│   │   ├── fund_list.py
│   │   ├── fund_nav.py
│   │   └── fund_holdings.py
│   └── static/                # Web 前端
│       ├── index.html
│       ├── app.js
│       └── style.css
└── miniprogram/               # 微信小程序
    ├── app.js / app.json
    ├── pages/index/           # 主页面
    ├── components/ec-canvas/  # ECharts 图表组件
    └── utils/api.js           # API 封装
```

## API

| 端点 | 说明 |
|---|---|
| `GET /api/funds/search?q=` | 搜索基金（DB → 东方财富 → 兜底） |
| `GET /api/funds/{code}` | 基金详情 + 指标 + 持仓 |
| `GET /api/funds/{code}/nav-history?period=` | 净值历史 |
| `GET /api/funds/{code}/metrics?period=` | 指标数据（含 PE） |
| `GET /api/funds/{code}/holdings` | 前十大持仓 |
| `GET /api/funds/{code}/dca?amount=&years=` | 定投回测 |
| `GET /api/funds` | 全部基金列表 |
| `GET /health` | 健康检查 |

## 数据来源

东方财富公开接口：`rankhandler.aspx`（基金列表） / `pingzhongdata/{code}.js`（净值） / `FundArchivesDatas.aspx`（持仓） / `push2.eastmoney.com`（PE）

## 免责声明

数据来源东方财富，可能存在延迟或误差。内容仅供参考，不构成投资建议。过往业绩不预示未来表现。定投回测基于历史数据推算，不代表未来收益。
