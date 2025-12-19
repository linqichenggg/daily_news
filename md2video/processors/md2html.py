"""Convert markdown to HTML with timeline support."""
import asyncio
import json
import re
import sys
import argparse
import yaml
import os
import logging
from pathlib import Path
from openai import AsyncOpenAI
from dotenv import load_dotenv
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载 .env 文件
load_dotenv()

# 导入公共模块
from utils.paths import get_output_dir, get_log_file_path

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(get_log_file_path("md2html"))
    ]
)
logger = logging.getLogger(__name__)

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent))

async def read_file_content(file_path: Path) -> str:
    """读取文件内容"""
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        raise

def parse_markdown_content(content: str) -> list:
    """解析Markdown内容为新闻条目列表"""
    # 移除分隔符
    content = re.sub(r'---+', '', content)
    
    if not content.strip().startswith('##'):
        if '##' in content:
            content = f"## 单机游戏日报\n{content.split('##')[0]}\n##" + '##'.join(content.split('##')[1:])
        else:
            content = f"## 单机游戏日报\n{content}"
    
    sections = re.split(r'(?m)^##\s+', content)
    return [section.strip() for section in sections if section.strip()]

async def save_html_page(html_content: str, file_path: Path):
    """保存HTML页面"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(html_content, encoding='utf-8')
    logger.info(f"已保存HTML页面到 {file_path}")

async def create_index_page(titles: list, summaries: list, output_dir: Path, index_template: str):
    """创建目录页面 (使用新模板)，支持根据新闻数量自动调整布局"""
    logger.info("正在生成目录页...")
    
    news_count = len(titles)
    logger.info(f"新闻数量: {news_count}，自动调整布局...")
    
    # 根据新闻数量动态调整样式
    # 布局配置：[新闻数量范围, 标题字号, 摘要字号, 卡片内边距, 网格间距, 摘要最大长度]
    layout_configs = {
        (1, 4): (32, 24, 25, "30px 60px", 50),      # 1-4条：标准布局
        (5, 6): (28, 22, 22, "25px 50px", 45),      # 5-6条：略微缩小
        (7, 8): (26, 20, 20, "20px 40px", 38),      # 7-8条：紧凑布局
        (9, 10): (24, 18, 18, "15px 35px", 32),     # 9-10条：很紧凑
    }
    
    # 选择合适的配置
    title_size, summary_size, padding, gap, summary_len = (32, 24, 25, "30px 60px", 50)  # 默认值
    for (min_count, max_count), config in layout_configs.items():
        if min_count <= news_count <= max_count:
            title_size, summary_size, padding, gap, summary_len = config
            break
    
    # 如果新闻超过10条，使用最紧凑配置
    if news_count > 10:
        title_size, summary_size, padding, gap, summary_len = (22, 16, 16, "12px 30px", 28)
        logger.warning(f"新闻数量({news_count})过多，使用超紧凑布局，建议控制在10条以内")
    
    # 生成动态CSS
    dynamic_css = f"""
    <style>
        .news-title {{
            font-size: {title_size}px !important;
        }}
        .news-summary {{
            font-size: {summary_size}px !important;
        }}
        .news-item {{
            padding: {padding}px !important;
        }}
        .news-grid {{
            gap: {gap} !important;
        }}
    </style>
    """
    
    # 生成新闻条目HTML
    news_items_html = ""
    for i, (title, summary) in enumerate(zip(titles, summaries), 1):
        clean_title = title.replace('##', '').strip() or f"新闻 {i}"
        # 根据新闻数量动态限制摘要长度
        if len(summary) > summary_len:
            summary = summary[:summary_len-3] + "..."
        
        news_items_html += f'''
            <div class="news-item">
                <div class="news-number">{i:02d}</div>
                <div class="news-content">
                    <div class="news-title">{clean_title}</div>
                    <div class="news-summary">{summary}</div>
                </div>
            </div>
'''
    
    # 替换模板占位符
    from datetime import datetime, timedelta
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    # 显示明天的日期（因为是提前一天生成第二天的早报）
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = f"{tomorrow.year}年{tomorrow.month:02d}月{tomorrow.day:02d}日 星期{weekdays[tomorrow.weekday()]}"
    
    index_content = index_template.replace('{{DATE}}', date_str)
    index_content = index_content.replace('{{NEWS_ITEMS}}', news_items_html)
    
    # 在 </head> 前插入动态CSS
    index_content = index_content.replace('</head>', f'{dynamic_css}</head>')
    
    # 保存目录页
    index_path = output_dir / "index.html"
    index_path.write_text(index_content, encoding='utf-8')
    logger.info(f"已保存目录页到 {index_path}（应用{news_count}条新闻的自适应布局）")

async def generate_html_for_news(news_content: str, client: AsyncOpenAI, system_prompt: str, template: str, index: int) -> tuple[str, str]:
    """为新闻生成HTML页面 (使用模板注入)，返回 (html_content, summary)"""
    logger.info(f"正在为新闻 {index+1} 生成HTML页面...")
    
    try:
        # 先用代码替换日期（不依赖 LLM）
        from datetime import datetime, timedelta
        weekdays = ['一', '二', '三', '四', '五', '六', '日']
        # 显示明天的日期（因为是提前一天生成第二天的早报）
        tomorrow = datetime.now() + timedelta(days=1)
        date_str = f"{tomorrow.year}年{tomorrow.month:02d}月{tomorrow.day:02d}日 星期{weekdays[tomorrow.weekday()]}"
        template = template.replace('{{DATE}}', date_str)
        
        # 构建包含模板的用户提示词
        user_prompt = f"""
Task: Fill the provided HTML template with the news content.

News Content:
{news_content}

HTML Template:
{template}

Requirements:
1. Return the FULL HTML code.
2. Do NOT change the CSS or structure of the template.
3. Replace `{{{{NUMBER}}}}` with the number "{index+1:02d}".
4. Replace `{{{{TITLE}}}}` with the news headline.
5. Replace `{{{{SUMMARY}}}}` with a 1-sentence summary (around 30-40 Chinese characters).
6. Replace `{{{{CONTENT}}}}` with the full news body (wrap paragraphs in <p> tags).
7. Ensure all text is in Chinese.
8. IMPORTANT: The content must fit within a single 1920x1080 page. Summarize the body text to approximately 100-200 Chinese characters to prevent overflow. Keep it concise.
"""

        # 准备请求参数
        completion_params = {
            "model": client.model,
            "temperature": 0.3,  # 降低温度以确保遵循模板
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        logger.info(f"正在请求 {client.model} API（新闻 {index+1}）...")
        logger.info(f"超时设置: 300秒, 重试次数: 5次")
        
        response = await client.chat.completions.create(**completion_params)
        clean_response = response.choices[0].message.content.strip()
        logger.info(f"✅ API 响应成功，内容长度: {len(clean_response)} 字符")
        
        if clean_response.startswith("```html"):
            clean_response = clean_response[7:]
        elif clean_response.startswith("```"):
            clean_response = clean_response[3:]
        
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        
        clean_response = clean_response.strip()

        # 提取摘要用于目录页
        summary = ""
        summary_match = re.search(r'<div class="summary">(.*?)</div>', clean_response, re.DOTALL)
        if summary_match:
            summary = re.sub(r'<[^>]+>', '', summary_match.group(1)).strip()
        else:
            # 如果没找到，尝试从新闻内容提取第一句话
            lines = news_content.split('\n')
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    summary = line.strip()[:40] + "..."
                    break

        if not clean_response.startswith(("<!DOCTYPE", "<html")):
            error_msg = f"❌ LLM返回的内容不是有效的HTML（新闻 {index+1}）"
            logger.error(error_msg)
            logger.error(f"返回内容: {clean_response[:200]}...")
            raise ValueError(error_msg)
        
        return clean_response, summary
    except Exception as e:
        logger.error(f"❌ 生成HTML时发生错误（新闻 {index+1}）: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误详情: {str(e)}")
        logger.error(f"⚠️ 不使用降级方案，抛出异常...")
        raise  # 重新抛出异常，确保失败时停止执行

async def main(content_path=None):
    """
    生成新闻 HTML 页面。
    - content_path 传入时优先使用（可为 Path 或 str，支持绝对路径）
    - 未传入时，回退到命令行参数；再回退到 env: NEWS_MD_PATH；最后默认 newsText.md
    """
    if content_path is None:
        # 解析命令行参数（兼容命令行调用）
        parser = argparse.ArgumentParser(description="生成HTML静态页面")
        parser.add_argument("--output", "-o", default="html_pages", help="HTML页面输出目录")
        parser.add_argument(
            "--content",
            "-c",
            default=os.getenv("NEWS_MD_PATH", "newsText.md"),
            help="内容文件路径（可为绝对路径）"
        )
        args = parser.parse_args()
        content_path = Path(args.content)
    else:
        content_path = Path(content_path)

    try:
        # 获取标准输出目录
        output_dir = get_output_dir("html")
        
        # 读取内容文件
        md_content = await read_file_content(content_path)
        
        # 读取HTML模板 - 新闻详情页模板
        detail_template_path = Path(project_root) / "templates" / "news_detail_template.html"
        if detail_template_path.exists():
            detail_template_content = detail_template_path.read_text(encoding='utf-8')
            logger.info(f"已加载新闻详情页模板: {detail_template_path}")
        else:
            logger.warning(f"未找到新闻详情页模板: {detail_template_path}，尝试使用旧模板")
            # 降级到旧模板
            old_template_path = Path(project_root) / "templates" / "news_template.html"
            if old_template_path.exists():
                detail_template_content = old_template_path.read_text(encoding='utf-8')
                logger.info(f"已加载旧模板: {old_template_path}")
            else:
                detail_template_content = "<html><body><h1>Error: Template not found</h1></body></html>"
        
        # 读取目录页模板
        index_template_path = Path(project_root) / "templates" / "index_template.html"
        if index_template_path.exists():
            index_template_content = index_template_path.read_text(encoding='utf-8')
            logger.info(f"已加载目录页模板: {index_template_path}")
        else:
            logger.warning(f"未找到目录页模板: {index_template_path}")
            index_template_content = None

        # 读取配置文件
        with open('llmConfig.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            md2html_config = config['md2html']
        
        # 从环境变量获取 API key
        api_key = os.getenv('LLM_API_KEY')
        if not api_key:
            raise ValueError("未找到环境变量 LLM_API_KEY，请在 .env 文件中设置")
        
        # 创建OpenAI客户端
        # DeepSeek-V3 模型较大，需要更长的超时时间
        client = AsyncOpenAI(
            base_url=md2html_config['base_url'],
            api_key=api_key,
            timeout=300.0,   # 超时时间：5分钟（DeepSeek-V3需要更长时间）
            max_retries=5    # 重试次数：5次（确保成功）
        )
        # 设置模型名称
        client.model = md2html_config['name']
        
        # 解析内容
        news_items = parse_markdown_content(md_content)
        logger.info(f"共解析出 {len(news_items)} 条新闻")
        
        # 处理每条新闻
        file_paths = []
        titles = []
        summaries = []
        total_news = len(news_items)
        
        for i, news_item in enumerate(news_items):
            logger.info(f"\n{'='*60}")
            logger.info(f"📰 处理进度: {i+1}/{total_news}")
            logger.info(f"{'='*60}")
            
            title_match = re.search(r'^## (.+?)(\n|$)', news_item)
            title = f"## {title_match.group(1).strip()}" if title_match else f"## 新闻 {i+1}"
            titles.append(title)
            
            # 添加重试间隔（避免API速率限制）
            if i > 0:
                import asyncio
                wait_time = 3  # 每个新闻之间等待3秒
                logger.info(f"⏳ 等待 {wait_time} 秒后处理下一条新闻（避免API限流）...")
                await asyncio.sleep(wait_time)
            
            # 生成并保存HTML，同时获取摘要
            try:
                html_content, summary = await generate_html_for_news(
                    news_item, 
                    client, 
                    md2html_config['system_prompt'], 
                    detail_template_content,
                    i
                )
                summaries.append(summary)
                
                file_path = output_dir / f"news_{i+1}.html"
                await save_html_page(html_content, file_path)
                file_paths.append(file_path)
                logger.info(f"✅ 新闻 {i+1}/{total_news} 生成成功！")
            except Exception as e:
                logger.error(f"❌ 新闻 {i+1}/{total_news} 生成失败！")
                logger.error(f"请检查 DeepSeek API 连接或切换到其他模型")
                raise  # 失败时停止所有处理
        
        # 创建目录页（如果有模板）
        if index_template_content:
            await create_index_page(titles, summaries, output_dir, index_template_content)
               
        logger.info("处理完成！")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())