# 基金多维度分析平台

一站式基金数据分析工具，输入基金代码或名称即可查看年化收益、最大回撤、夏普比率、PE 估值、定投回测等多维度指标。

## 功能特性

### 基金搜索与发现
- 支持按基金代码或名称搜索
- 自动从东方财富获取 QDII 基金列表并存入本地数据库

### 多维度指标
| 指标 | 说明 | 支持周期 |
|------|------|----------|
| 年化收益 | 复利年化回报率 (CAGR) | 1年 / 3年 / 5年 / 今年以来 / 成立以来 |
| 最大回撤 | 历史最大净值跌幅，含峰值与谷底日期 | 1年 / 3年 / 5年 / 成立以来 |
| 波动率 | 年化日收益标准差 | 1年 / 3年 / 5年 |
| 夏普比率 | (年化收益-无风险利率) / 波动率 | 1年 / 3年 / 5年 |
| 索提诺比率 | 仅用下行波动率的分母修正 | 1年 / 3年 |
| 卡玛比率 | 年化收益 / \|最大回撤\| | 1年 / 3年 |
| 胜率 | 日收益为正的天数占比 | 1年 / 3年 |
| PE 比率 | 基于前十大持仓加权调和平均的市盈率 | 实时 |

### 可视化图表
- **净值走势图** — 单位净值 + 累计净值双线图
- **回撤曲线** — 实时回撤百分比面积图

### 定投回测
- 按月定额定投模拟，支持自定义金额（≥100）和年限（1-10年）
- 与一次性投入对比收益
- 定投过程可视化（累计投入 / 持仓市值 / 持仓成本 / 基金净值）
- 自动分析水下期数和成本偏离

### 持仓分析
- 前十大持仓明细（股票代码、名称、权重、报告期）

### 指标解读
- 点击任意指标卡片弹出详细说明（公式、评级标准、投资含义）

### 投资大师视角
- API 接口提供巴菲特、芒格、段永平、彼得·林奇、博格、霍华德·马克斯六位大师风格的教育性点评

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| 数据库 | SQLite + SQLAlchemy ORM |
| 前端 | 原生 JavaScript SPA |
| 图表 | Chart.js 4.4 |
| 数据源 | 东方财富公开 API |

## 项目结构

```
├── backend/
│   ├── main.py              # FastAPI 应用入口，所有 API 路由
│   ├── models.py            # SQLAlchemy 数据模型 (Fund / Holding / FundNav)
│   ├── database.py          # 数据库引擎与初始化
│   ├── config.py            # 配置常量（API URL 等）
│   ├── requirements.txt     # Python 依赖
│   ├── data.db              # SQLite 数据库（运行时生成）
│   ├── calculator/
│   │   ├── metrics.py       # 所有指标计算 + PE比率 + 定投回测
│   │   └── commentary.py    # 投资大师点评生成
│   ├── scraper/
│   │   ├── fund_list.py     # QDII 基金列表抓取
│   │   ├── fund_nav.py      # 净值历史抓取
│   │   └── fund_holdings.py # 前十大持仓抓取
│   └── static/
│       ├── index.html       # SPA 入口
│       ├── app.js           # 前端状态管理与交互
│       └── style.css        # 样式
└── README.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端 SPA |
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/funds` | 基金列表 |
| `GET` | `/api/funds/search?q=` | 搜索/添加基金 |
| `GET` | `/api/funds/{code}` | 基金详情（含指标+持仓） |
| `GET` | `/api/funds/{code}/nav-history?period=` | 净值历史（period: 1y/3y/5y/ytd/all） |
| `GET` | `/api/funds/{code}/metrics?period=` | 指标数据（含 PE） |
| `GET` | `/api/funds/{code}/holdings` | 前十大持仓 |
| `GET` | `/api/funds/{code}/dca?amount=&years=` | 定投回测 |
| `GET` | `/api/funds/{code}/commentary` | 投资大师点评 |

## 快速开始

### 环境要求
- Python 3.9+
- pip

### 安装与运行

```bash
# 克隆项目
git clone <repo-url>
cd guzhi

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
python backend/main.py
```

浏览器打开 http://localhost:8000 即可使用。

## 数据来源

所有数据来自东方财富公开接口：

| 数据类型 | 来源 |
|----------|------|
| 基金列表 | `fund.eastmoney.com/data/rankhandler.aspx` |
| 净值历史 | `fund.eastmoney.com/pingzhongdata/{code}.js` |
| 持仓数据 | `fundf10.eastmoney.com/FundArchivesDatas.aspx` |
| 股票 PE | `push2.eastmoney.com/api/qt/stock/get` |

## 免责声明

- 数据来源：东方财富，可能存在延迟或误差
- 内容仅供参考，不构成投资建议
- 过往业绩不预示未来表现
- 定投回测基于历史数据推算，不代表未来收益
