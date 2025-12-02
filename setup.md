# 项目配置指南

## 环境配置

### 1. API Keys 配置

#### LLM API (DeepSeek-V3)
用于生成 HTML 新闻内容
1. 在项目根目录创建 `.env` 文件
2. 设置 SiliconFlow API key：
   ```
   LLM_API_KEY=你的_SiliconFlow_API_key
   ```
   （使用 SiliconFlow 平台访问 DeepSeek-V3 模型）

#### Minimax API
用于语音合成（TTS）
1. 在 `minimax/config.env` 文件中设置：
   ```
   MINIMAX_API_KEY=你的Minimax_API_key
   ```

### 2. 依赖安装
```bash
pip install -r requirements.txt
```

### 3. 运行项目
```bash
# Gemini API 测试（可选，仅用于测试）
python gemini-api.py

# Minimax TTS 语音合成
cd minimax
python main.py

# 视频生成（主要功能）
cd md2video
python main.py
```

## 安全注意事项

- 所有包含API keys的文件都被 `.gitignore` 忽略
- 不要将 `.env` 或 `minimax/config.env` 文件提交到Git
