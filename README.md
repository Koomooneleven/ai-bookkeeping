# AI 自动记账系统

双击 iPhone 背面 → 输入消费内容 → AI 自动识别金额/货币/分类 → 记录到云端。

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 DeepSeek API Key 和自定义的 API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
API_KEY=my-secret-key-123
```

- `DEEPSEEK_API_KEY`：在 [platform.deepseek.com](https://platform.deepseek.com) 注册获取
- `API_KEY`：自定义一个密钥，用于快捷指令访问 API

### 3. 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 打开仪表盘

浏览器访问 `http://localhost:8000/dashboard`

### 5. 配置 iPhone 快捷指令

详见 [shortcuts/README.md](shortcuts/README.md)

## 部署到 Railway

1. Fork 本项目到 GitHub
2. 在 [Railway](https://railway.app) 创建新项目，选择 Deploy from GitHub repo
3. 设置环境变量：
   - `DEEPSEEK_API_KEY`
   - `API_KEY`
4. 部署完成后获得 `https://xxx.up.railway.app` 地址
5. 将此地址填入快捷指令

## API 文档

### 认证

所有 API 需要在请求头中携带 `X-API-Key`

### 添加账单

```bash
curl -X POST https://你的域名/api/transactions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "午餐麦当劳35元"}'
```

### 查询账单

```bash
curl "https://你的域名/api/transactions?page=1&page_size=20" \
  -H "X-API-Key: your-api-key"
```

### 月度统计

```bash
curl "https://你的域名/api/stats/monthly" \
  -H "X-API-Key: your-api-key"
```

### 导出 CSV

```bash
curl "https://你的域名/api/stats/export/csv" \
  -H "X-API-Key: your-api-key" \
  -o 账单导出.csv
```
