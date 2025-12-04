import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)  # 切换工作目录到 md2video

from processors import (
    md2html_main,
    html2img_main,
    img2video_main,
    md2audio_main
)
from utils.paths import get_log_file_path

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(get_log_file_path("main"))
    ]
)
logger = logging.getLogger(__name__)

async def main():
    try:

        # 4. Markdown转音频
        logger.info("开始执行Markdown到音频的转换...")
        md2audio_main("audioText.md")  # 这个函数不是异步的
        logger.info("Markdown到音频转换完成")

        # 1. Markdown转HTML
        logger.info("开始执行Markdown到HTML的转换...")
        await md2html_main()
        logger.info("Markdown到HTML转换完成")

        # 2. HTML转图片
        logger.info("开始执行HTML到图片的转换...")
        await html2img_main()
        logger.info("HTML到图片转换完成")

        # 3. 图片转视频
        logger.info("开始执行图片到视频的转换...")
        await img2video_main()
        logger.info("图片到视频转换完成")

        logger.info("所有处理步骤已完成！")

    except Exception as e:
        logger.error(f"处理过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    # 运行主程序 (日志目录由 get_log_file_path 自动创建)
    asyncio.run(main()) 