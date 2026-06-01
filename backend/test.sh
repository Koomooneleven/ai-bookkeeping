#!/bin/bash
# AI 记账系统测试脚本
# 用法: bash test.sh

API_KEY="jizhang2026"
BASE="http://localhost:8000"

echo "===== 1. 测试账单列表 ====="
curl -s "$BASE/api/transactions" -H "X-API-Key: $API_KEY" | python -m json.tool

echo ""
echo "===== 2. 新增账单 (中文) ====="
printf '{"text":"午餐麦当劳35元"}' > /tmp/test_body.json
curl -s -X POST "$BASE/api/transactions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_body.json | python -m json.tool

echo ""
echo "===== 3. 新增账单 (英文) ====="
printf '{"text":"Starbucks coffee $4.5"}' > /tmp/test_body.json
curl -s -X POST "$BASE/api/transactions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_body.json | python -m json.tool

echo ""
echo "===== 4. 分类统计 ====="
curl -s "$BASE/api/stats/category" -H "X-API-Key: $API_KEY" | python -m json.tool

echo ""
echo "===== 5. 月度趋势 ====="
curl -s "$BASE/api/stats/trend" -H "X-API-Key: $API_KEY" | python -m json.tool

echo ""
echo "===== 6. CSV导出 ====="
curl -s "$BASE/api/stats/export/csv" -H "X-API-Key: $API_KEY"

echo ""
echo "===== 完成! 打开 http://localhost:8000/dashboard 查看仪表盘 ====="
