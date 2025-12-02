import asyncio
import argparse
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("错误: 请先安装 playwright 库")
    print("pip install playwright")
    print("playwright install chromium")
    sys.exit(1)

# 导入公共模块
from utils.paths import get_output_dir

# 确保logs目录存在
Path("logs").mkdir(exist_ok=True)

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_html2img.log")
    ]
)
logger = logging.getLogger(__name__)

async def html_to_image(html_file, output_name, width=1920, height=1080):
    """将HTML文件转换为图片 (使用 Playwright)"""
    output_dir = get_output_dir("images")
    output_image = output_dir / f"{output_name}.png"
    
    try:
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': width, 'height': height})
            
            # 获取HTML文件的绝对路径
            html_path = os.path.abspath(html_file)
            file_url = f"file://{html_path}"
            
            logger.info(f"正在加载页面: {file_url}")
            
            # 加载页面并等待网络空闲（确保资源加载完成）
            await page.goto(file_url, wait_until='networkidle')
            
            # 截图
            await page.screenshot(path=str(output_image))
            logger.info(f"已保存截图到 {output_image}")
            
            await browser.close()
            return True
            
    except Exception as e:
        logger.error(f"截图过程中出错: {e}")
        return False

async def process_html_directory(html_dir, width=1920, height=1080):
    """处理HTML目录下的所有文件"""
    html_path = Path(html_dir)
    if not html_path.exists():
        raise FileNotFoundError(f"HTML目录不存在: {html_dir}")
    
    # 获取所有HTML文件
    html_files = []
    
    # 首先添加 index.html（目录页），如果存在的话
    index_file = html_path / "index.html"
    if index_file.exists():
        html_files.append(index_file)
        logger.info("找到目录页 index.html，将作为第一页")
    
    # 然后添加所有新闻页面并排序
    news_files = [f for f in html_path.glob("*.html") if f.name != "index.html"]
    news_files.sort(key=lambda x: int(x.stem.split('_')[1]) if x.stem.startswith('news_') and x.stem.split('_')[1].isdigit() else float('inf'))
    html_files.extend(news_files)
    
    logger.info(f"找到 {len(html_files)} 个HTML文件待处理")
    
    success_count = 0
    
    # 使用 Playwright 处理所有文件（复用浏览器实例更高效）
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={'width': width, 'height': height})
            
            for html_file in html_files:
                output_name = html_file.stem
                output_dir = get_output_dir("images")
                output_image = output_dir / f"{output_name}.png"
                
                try:
                    page = await context.new_page()
                    html_abs_path = os.path.abspath(html_file)
                    file_url = f"file://{html_abs_path}"
                    
                    logger.info(f"正在处理: {html_file.name}")
                    await page.goto(file_url, wait_until='networkidle')
                    await page.screenshot(path=str(output_image))
                    logger.info(f"截图成功: {output_image.name}")
                    
                    await page.close()
                    success_count += 1
                except Exception as e:
                    logger.error(f"处理 {html_file.name} 失败: {e}")
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"批量处理过程中出错: {e}")
    
    return success_count

async def main():
    parser = argparse.ArgumentParser(
        description="将HTML页面转换为截图 (Playwright版)",
        formatter_class=argparse.RawTextHelpFormatter)
    
    # 添加两种模式的参数组
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--manual", action="store_true",
                         help="手动模式，需要指定HTML文件和输出路径")
    mode_group.add_argument("--auto", action="store_true", default=True,
                         help="自动处理最新的输出目录中的HTML文件（默认模式）")
    
    parser.add_argument("--html", help="手动模式：要截图的HTML文件路径")
    parser.add_argument("--output", "-o", help="手动模式：截图保存路径")
    parser.add_argument("--width", "-w", type=int, default=1920,
                      help="截图宽度，默认1920像素")
    parser.add_argument("--height", "-ht", type=int, default=1080,
                      help="截图高度，默认1080像素")
    
    args = parser.parse_args()
    
    try:
        if args.manual:
            if not (args.html and args.output):
                parser.error("手动模式需要同时指定 --html 和 --output 参数")
            # 单文件处理模式
            success = await html_to_image(args.html, args.output, args.width, args.height)
            if not success:
                sys.exit(1)
        else:
            # 自动模式
            output_dir = Path("output")
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找最新的日期目录
            date_dirs = sorted([d for d in output_dir.glob("*") 
                              if d.is_dir() and d.name.isdigit()], reverse=True)
            
            if not date_dirs:
                # 如果没有目录，尝试使用今天的
                today_dir = output_dir / datetime.now().strftime("%Y%m%d")
                today_dir.mkdir(exist_ok=True)
                date_dirs = [today_dir]
            
            latest_dir = date_dirs[0]
            html_dir = latest_dir / "html"
            
            # 确保images目录存在
            images_dir = latest_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            if not html_dir.exists():
                raise FileNotFoundError(f"HTML目录不存在: {html_dir}")
            
            logger.info(f"处理目录: {html_dir}")
            success_count = await process_html_directory(html_dir, args.width, args.height)
            logger.info(f"成功处理 {success_count} 个HTML文件")
            
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())