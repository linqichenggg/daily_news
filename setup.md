# 项目配置指南

## 环境配置

### 1. API Keys 配置

#### Gemini API
1. 复制 `.env.example` 为 `.env`（如果存在）
2. 在 `.env` 文件中设置：
   ```
   GEMINI_API_KEY=你的Gemini_API_key
   ```

#### Minimax API
1. 复制 `minimax/config.env.example` 为 `minimax/config.env`（如果存在）
2. 在 `minimax/config.env` 文件中设置：
   ```
   MINIMAX_API_KEY=你的Minimax_API_key
   ```

### 2. 依赖安装
```bash
pip install -r requirements.txt
```

### 3. 运行项目
```bash
# Gemini API 测试
python gemini-api.py

# Minimax TTS
cd minimax
python main.py

# 视频生成
cd md2video
python main.py
```

## 安全注意事项

- 所有包含API keys的文件都被 `.gitignore` 忽略
- 不要将 `.env` 或 `config.env` 文件提交到Git
- 分享项目时请提供 `.env.example` 和 `config.env.example` 模板文件
