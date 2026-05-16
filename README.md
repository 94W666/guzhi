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

| 层 | 技术 |
|---|---|
| 后端 | Python 3 + FastAPI + SQLAlchemy + SQLite |
| 前端 | Vanilla JS SPA + Chart.js 4.4 |
| 数据源 | 东方财富公开 API |

## 快速开始

```bash
pip install -r backend/requirements.txt
python backend/main.py
```

浏览器打开 http://localhost:8000

## 项目结构

```
backend/
├── main.py               # FastAPI 应用 + 全部路由
├── models.py             # ORM 模型（Fund, Holding, FundNav）
├── database.py           # SQLite 连接与会话管理
├── config.py             # 配置常量
├── calculator/
│   └── metrics.py        # 指标计算引擎 + PE + DCA
├── scraper/
│   ├── fund_list.py      # 基金列表爬虫
│   ├── fund_nav.py       # 净值历史爬虫
│   └── fund_holdings.py  # 持仓爬虫
└── static/
    ├── index.html
    ├── app.js
    └── style.css
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
