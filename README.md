# 基金多维度分析平台

一站式基金数据分析工具，输入基金代码或名称即可查看年化收益、最大回撤、夏普比率、PE 估值、定投回测等多维度指标。

## 功能

### Web 版 & 小程序版共有

- **基金搜索**：代码或名称搜索，启动时预加载全市场 ~10000 只基金元数据到数据库，毫秒级响应
- **8 项核心指标**：年化收益、最大回撤、回撤修复天数、波动率、夏普比率、PE 比率、Calmar 比率、胜率
- **周期切换**：1年 / 3年 / 5年 / 成立以来，Web 端图表即时切换（本地缓存，零网络请求）
- **净值走势图**：单位净值 + 累计净值双线
- **回撤曲线**：从历史最高点算起的跌幅面积图
- **定投回测**：月定投模拟，含一次性买入对比 + 过程可视化 + 文字解读
- **前十大持仓**：股票代码、名称、权重、季报日期
- **指标解读**：点击任意指标卡片弹出公式说明与评级标准
- **全市场支持**：不限于特定类型，任意公募基金代码均可

### 小程序版特有

- **自选列表**：收藏基金，本地持久化存储，长按删除
- **DCA 参数可调**：金额、年限自由配置
- **云托管 + 本地双模式**：`useCloud` 开关一键切换

## 技术栈

| 层 | Web 版 | 小程序版 |
|---|---|---|
| 后端 | Python 3 + FastAPI + SQLAlchemy + SQLite | 同左 (CloudBase 云托管 + MySQL) |
| 前端 | Vanilla JS SPA + Chart.js 4.4 | WXML/WXSS/JS (零框架) |
| 部署 | uvicorn 单进程 | Docker + gunicorn + CloudBase |

## 快速开始

### Web 版

```bash
pip install -r backend/requirements.txt
python backend/main.py
# → http://localhost:8000
```

### 微信小程序版（本地开发）

1. 微信开发者工具打开 `miniprogram/` 目录
2. `app.js` 中设 `useCloud: false`
3. 开发者工具勾选"不校验合法域名"
4. 启动后端 `python backend/main.py`

### 微信小程序版（云托管上线）

1. 腾讯云开发控制台 → 云托管 → 新建服务
2. 环境变量配置 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/fund_db`
3. 推送代码后触发云托管构建/部署（`Dockerfile` 已就绪）
4. `app.js` 中设 `useCloud: true`，上传小程序

## 项目结构

```
├── Dockerfile                     # CloudBase 云托管部署
├── backend/                       # FastAPI 后端
│   ├── main.py                    # 应用入口 + 全部 API 路由 + 缓存层
│   ├── models.py                  # ORM: Fund, Holding, NavEstimate, FundNav
│   ├── database.py                # SQLite/MySQL 双引擎 + Session 管理
│   ├── config.py                  # 全局配置
│   ├── calculator/
│   │   ├── metrics.py             # 指标计算 + PE + DCA 回测
│   │   └── commentary.py          # 投资大师点评
│   ├── scraper/
│   │   ├── fund_list.py           # 基金列表爬虫 (rankhandler)
│   │   ├── fund_nav.py            # 净值历史爬虫 (pingzhongdata)
│   │   └── fund_holdings.py       # 持仓爬虫 (FundArchivesDatas)
│   └── static/                    # Web 前端 SPA
│       ├── index.html
│       ├── app.js
│       └── style.css
└── miniprogram/                   # 微信小程序
    ├── app.js / app.json          # 应用入口 + 全局配置
    ├── pages/index/               # 主页面
    │   ├── index.js / index.wxml / index.wxss
    └── utils/api.js               # API 封装 (wx.request / callContainer)
```

## API

| 端点 | 说明 |
|---|---|
| `GET /api/funds/search?q=` | 搜索基金（DB → 内存缓存 → pingzhongdata 兜底） |
| `GET /api/funds/{code}` | 基金详情 + 指标 + 持仓 + 数据摘要 |
| `GET /api/funds/{code}/nav-history?period=` | 净值历史 (1y/3y/5y/ytd/all) |
| `GET /api/funds/{code}/metrics?period=` | 指标数据（含 PE） |
| `GET /api/funds/{code}/holdings` | 前十大持仓 |
| `GET /api/funds/{code}/dca?amount=&years=` | 定投回测 |
| `GET /api/funds` | 全部基金列表 |
| `GET /health` | 健康检查（含数据库连通性） |

## 数据库

- **本地**: SQLite (`backend/data.db`)，零配置
- **云端**: MySQL，通过 `DATABASE_URL` 环境变量切换，启动时自动建库建表
- 启动时自动从东方财富拉取全市场 ~10000 只基金元数据并持久化，搜索永远命中 DB
- 净值/持仓按需拉取，当天数据缓存

## 数据来源

东方财富公开接口：`rankhandler.aspx` / `pingzhongdata/{code}.js` / `FundArchivesDatas.aspx` / `push2.eastmoney.com`

## 免责声明

数据来源东方财富，可能存在延迟或误差。内容仅供参考，不构成投资建议。过往业绩不预示未来表现。定投回测基于历史数据推算，不代表未来收益。
