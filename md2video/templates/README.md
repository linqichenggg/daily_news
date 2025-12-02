# 单机游戏日报 模板使用说明

## 📁 文件说明

### 模板文件（用于Python代码）

1. **index_template.html** - 目录页模板
   - 用于展示5-10条新闻的概览
   - 使用双栏网格布局
   - 包含占位符：`{{DATE}}`, `{{NEWS_ITEMS}}`

2. **news_detail_template.html** - 新闻详情页模板
   - 用于展示单条新闻的完整内容
   - 三栏报纸风格布局
   - 包含占位符：`{{DATE}}`, `{{NUMBER}}`, `{{TITLE}}`, `{{SUMMARY}}`, `{{CONTENT}}`

### 演示文件（可直接在浏览器查看）

1. **demo_index.html** - 目录页演示
2. **demo_news_detail.html** - 新闻详情页演示

## 🎨 设计特点

### 视觉风格
- 📰 **报纸风格设计**：经典双线边框，宋体标题
- 🎨 **配色方案**：
  - 背景色：米色 (#F9F7F1)
  - 强调色：深红色 (#8B0000)
  - 主文本：深灰 (#222222)
  - 次要文本：灰色 (#555555)

### 布局特点
- 📐 **分辨率**：1920x1080（适合视频）
- 📱 **响应式**：固定尺寸，针对截图优化
- 🎯 **网格布局**：目录页采用2x3网格（可容纳6条新闻）

## 💻 Python代码集成示例

### 目录页生成示例

```python
from datetime import datetime

# 读取模板
with open('templates/index_template.html', 'r', encoding='utf-8') as f:
    template = f.read()

# 准备新闻数据
news_list = [
    {"number": "01", "title": "标题1", "summary": "摘要1"},
    {"number": "02", "title": "标题2", "summary": "摘要2"},
    # ...
]

# 生成新闻项HTML
news_items_html = ""
for news in news_list:
    news_items_html += f'''
    <div class="news-item">
        <div class="news-number">{news["number"]}</div>
        <div class="news-content">
            <div class="news-title">{news["title"]}</div>
            <div class="news-summary">{news["summary"]}</div>
        </div>
    </div>
    '''

# 替换占位符
date_str = datetime.now().strftime('%Y年%m月%d日 星期%w')
html = template.replace('{{DATE}}', date_str)
html = html.replace('{{NEWS_ITEMS}}', news_items_html)

# 保存文件
with open('output/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

### 新闻详情页生成示例

```python
# 读取模板
with open('templates/news_detail_template.html', 'r', encoding='utf-8') as f:
    template = f.read()

# 准备新闻数据
news_data = {
    "number": "01",
    "title": "OpenAI推出GPT-5预览版本",
    "summary": "OpenAI在内部测试中展示了GPT-5的强大能力...",
    "content": "<p>段落1</p><p>段落2</p><p>段落3</p>"
}

# 替换占位符
html = template.replace('{{DATE}}', date_str)
html = html.replace('{{NUMBER}}', news_data["number"])
html = html.replace('{{TITLE}}', news_data["title"])
html = html.replace('{{SUMMARY}}', news_data["summary"])
html = html.replace('{{CONTENT}}', news_data["content"])

# 保存文件
with open('output/news_1.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

## 🎬 视频制作流程建议

1. **生成目录页** → 截图作为视频开头（5-8秒）
2. **生成新闻详情页** → 每条新闻独立截图（根据语音时长调整）
3. **使用FFmpeg合成** → 结合音频和字幕生成最终视频

## 🔧 自定义建议

### 调整新闻条数
目录页的网格布局可以容纳：
- 6条新闻（3行 x 2列）- 推荐
- 8条新闻（4行 x 2列）- 紧凑
- 4条新闻（2行 x 2列）- 宽松

需要调整 `.news-grid` 的 `gap` 属性。

### 修改配色
在 `:root` 中修改CSS变量：
```css
:root {
    --bg-color: #F9F7F1;        /* 背景色 */
    --accent-color: #8B0000;     /* 强调色 */
    --text-primary: #222222;     /* 主文本 */
    --text-secondary: #555555;   /* 次要文本 */
}
```

## 📝 注意事项

1. 确保使用UTF-8编码保存文件
2. 目录页最多显示6条新闻效果最佳
3. 新闻详情页内容建议控制在300-500字
4. 字体依赖系统安装的"PingFang SC"和"Songti SC"

## 🌐 浏览器查看

直接用浏览器打开 `demo_index.html` 和 `demo_news_detail.html` 查看效果。

建议使用Chrome或Safari浏览器，并将浏览器窗口缩放至1920x1080以获得最佳预览效果。

