#!/usr/bin/env python3
"""快速测试HTML生成，无需生成完整视频"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from processors.md2html import main as md2html_main

async def main():
    print("=" * 60)
    print("🎮 仅生成HTML页面测试")
    print("=" * 60)
    print()
    
    try:
        # 只运行HTML生成步骤
        await md2html_main()
        
        print()
        print("=" * 60)
        print("✅ HTML生成完成！")
        print("=" * 60)
        print()
        print("📂 输出目录：output/[日期]/html/")
        print("📄 文件列表：")
        print("   - index.html（目录页）")
        print("   - news_1.html, news_2.html, ...（详情页）")
        print()
        print("🌐 在浏览器中打开查看效果：")
        
        # 查找最新的输出目录
        output_dir = Path("output")
        if output_dir.exists():
            date_dirs = sorted([d for d in output_dir.glob("*") 
                              if d.is_dir() and d.name.isdigit()], reverse=True)
            if date_dirs:
                latest_dir = date_dirs[0]
                index_path = latest_dir / "html" / "index.html"
                if index_path.exists():
                    print(f"   open {index_path}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

