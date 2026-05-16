#!/bin/bash
# 基金分析平台性能测试脚本
BASE="https://fund-backend-258622-9-1433815187.sh.run.tcloudbase.com"

echo "========================================"
echo "  基金分析平台 — 端到端性能测试"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 测试函数：计时 + 显示结果摘要
test_api() {
  local label="$1"
  local url="$2"
  local start=$(date +%s%N)
  local resp=$(curl -s -w "\n%{time_total}" "$url" 2>/dev/null)
  local time=$(echo "$resp" | tail -1)
  local body=$(echo "$resp" | head -n -1)
  local sec=$(printf "%.2f" "$time")
  local chars=$(echo "$body" | wc -c)
  echo "  [$sec s] $label (${chars} bytes)"
}

echo ""
echo "--- 第1轮：冷启动（首次查询，需拉东方财富+算指标）---"
echo ""
echo "1.1 搜索 017642（库中无此基金）"
test_api "搜索" "$BASE/api/funds/search?q=017642"

echo ""
echo "1.2 加载基金详情（自动发现+拉净值+算指标+拉持仓+算DCA）"
test_api "详情" "$BASE/api/funds/017642"

echo ""
echo "1.3 再次请求同一基金（当天缓存命中）"
test_api "详情(缓存)" "$BASE/api/funds/017642"

echo ""
echo "1.4 DCA 回测（默认1k/3y，已在详情计算时预热）"
test_api "DCA" "$BASE/api/funds/017642/dca?amount=1000&years=3"

echo ""
echo "--- 第2轮：库里已有的基金 ---"
echo ""
echo "2.1 搜索 005698（数据库命中）"
test_api "搜索" "$BASE/api/funds/search?q=005698"

echo ""
echo "2.2 加载详情（走当天缓存）"
test_api "详情" "$BASE/api/funds/005698"

echo ""
echo "2.3 DCA 缓存命中"
test_api "DCA" "$BASE/api/funds/005698/dca?amount=1000&years=3"

echo ""
echo "2.4 切换 DCA 参数（5年，缓存未命中需重算）"
test_api "DCA 5y" "$BASE/api/funds/005698/dca?amount=1000&years=5"

echo ""
echo "2.5 指标查询"
test_api "Metrics" "$BASE/api/funds/005698/metrics?period=1y"

echo ""
echo "--- 第3轮：库中已有基金的第二次请求（纯缓存）---"
echo ""
echo "3.1 详情再查"
test_api "详情" "$BASE/api/funds/005698"

echo ""
echo "3.2 DCA再查"
test_api "DCA" "$BASE/api/funds/005698/dca?amount=1000&years=3"

echo ""
echo "--- 第4轮：确认数据正确性 ---"
echo ""

echo "4.1 库中基金列表"
curl -s "$BASE/api/funds" | python3 -c "
import sys,json
funds = json.load(sys.stdin)
for f in funds:
    print(f'  {f[\"code\"]}  {f[\"name\"]}  ({f[\"fund_type\"]})')
"

echo ""
echo "4.2 005698 关键指标"
curl -s "$BASE/api/funds/005698" | python3 -c "
import sys,json
d = json.load(sys.stdin)
m = d['metrics']
print(f'  基金: {d[\"fund\"][\"name\"]}')
print(f'  年化收益: 1y={m[\"returns\"][\"1y\"]:.2%}  3y={m[\"returns\"][\"3y\"]:.2%}  inception={m[\"returns\"][\"since_inception\"]:.2%}')
print(f'  最大回撤: 1y={m[\"max_drawdown\"][\"1y\"][\"mdd\"]:.2%}  3y={m[\"max_drawdown\"][\"3y\"][\"mdd\"]:.2%}')
print(f'  持仓数量: {len(d[\"holdings\"])}')
print(f'  NAV记录: {d[\"data_summary\"][\"nav_records\"]}条 ({d[\"data_summary\"][\"nav_start\"]} ~ {d[\"data_summary\"][\"nav_end\"]})')
"

echo ""
echo "4.3 005698 DCA 结果"
curl -s "$BASE/api/funds/005698/dca?amount=1000&years=3" | python3 -c "
import sys,json
d = json.load(sys.stdin)
print(f'  定投周期: {d[\"total_months\"]}个月 ({d[\"start_date\"]}~{d[\"end_date\"]})')
print(f'  总投入: ¥{d[\"total_invested\"]:,.0f}')
print(f'  终值: ¥{d[\"final_value\"]:,.2f}')
print(f'  总收益率: {d[\"total_return_pct\"]:+.1f}%')
print(f'  年化: {d[\"annualized_return_pct\"]:+.1f}%')
print(f'  一次性买入: {d[\"lump_sum\"][\"return_pct\"]:+.1f}%')
print(f'  平均成本: {d[\"avg_cost_per_share\"]:.4f}  当前净值: {d[\"current_nav\"]:.4f}')
"

echo ""
echo "========================================"
echo "  测试完成"
echo "========================================"
