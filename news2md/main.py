#!/usr/bin/env python3
"""
news2md - 新闻采集与MD生成

使用方法:
    python main.py              # 完整流程：爬取 + 分析 + 生成MD
    python main.py --crawl      # 仅爬取数据
    python main.py --analyze    # 仅分析已有数据并生成MD
    python main.py --test       # 测试API连接
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# 加载环境变量（明确指定 .env 文件路径）
from dotenv import load_dotenv
env_path = project_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️ 未找到 .env 文件: {env_path}")
    print("   请创建 news2md/.env 文件并设置 GEMINI_API_KEY")

from crawlers import RedditCrawler, DM3Crawler
from analyzer import NewsAnalyzer
from generator import MarkdownGenerator


def get_output_dir() -> Path:
    """获取今日输出目录"""
    today = datetime.now().strftime("%Y%m%d")
    output_dir = Path(__file__).parent / "output" / today
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def crawl() -> Path:
    """爬取 Reddit + 3DM 数据"""
    print("\n" + "=" * 50)
    print("📡 步骤 1: 爬取新闻数据")
    print("=" * 50)
    
    all_posts = []
    
    # 1. 爬取 Reddit
    print("\n🔹 Reddit:")
    try:
        reddit_crawler = RedditCrawler()
        if reddit_crawler.test_connection():
            reddit_posts = reddit_crawler.crawl()
            all_posts.extend(reddit_posts)
            print(f"   ✅ 获取 {len(reddit_posts)} 条")
        else:
            print("   ⚠️ Reddit 连接失败，跳过")
    except Exception as e:
        print(f"   ⚠️ Reddit 爬取失败: {e}")
    
    # 2. 爬取 3DM
    print("\n🔹 3DM:")
    try:
        dm3_crawler = DM3Crawler()
        dm3_posts = dm3_crawler.crawl()
        all_posts.extend(dm3_posts)
        print(f"   ✅ 获取 {len(dm3_posts)} 条")
    except Exception as e:
        print(f"   ⚠️ 3DM 爬取失败: {e}")
    
    if not all_posts:
        raise RuntimeError("未获取到任何数据")
    
    print(f"\n📊 总计: {len(all_posts)} 条新闻")
    
    # 保存原始数据
    output_dir = get_output_dir()
    output_path = output_dir / "raw_posts.json"
    
    # 使用 Reddit 爬虫的 save_to_json 方法保存
    reddit_crawler = RedditCrawler()
    reddit_crawler.save_to_json(all_posts, output_path)
    
    return output_path


def analyze(json_path: Path) -> list:
    """分析新闻"""
    print("\n" + "=" * 50)
    print("🤖 步骤 2: Gemini 分析")
    print("=" * 50)
    
    # 读取数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    posts = data.get('posts', [])
    print(f"📖 读取 {len(posts)} 条帖子")
    
    # 分析
    analyzer = NewsAnalyzer()
    news_list = analyzer.analyze(posts)
    
    if not news_list:
        raise RuntimeError("分析未返回新闻")
    
    # 保存分析结果
    output_dir = json_path.parent
    result_path = output_dir / "analyzed_news.json"
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, ensure_ascii=False, indent=2, fp=f)
    print(f"✅ 分析结果已保存到 {result_path}")
    
    return news_list


def generate(news_list: list) -> dict:
    """生成 MD 文件"""
    print("\n" + "=" * 50)
    print("📝 步骤 3: 生成 Markdown")
    print("=" * 50)
    
    generator = MarkdownGenerator()
    return generator.save(news_list)


def test_connections():
    """测试 API 连接"""
    print("\n🔍 测试 API 连接...")
    
    print("\n1. Reddit RSS:")
    try:
        crawler = RedditCrawler()
        crawler.test_connection()
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n2. 3DM:")
    try:
        dm3 = DM3Crawler()
        posts = dm3.crawl()
        print(f"   ✅ 3DM 连接正常，获取 {len(posts)} 条新闻")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
    
    print("\n3. Gemini API:")
    try:
        analyzer = NewsAnalyzer()
        print("   ✅ Gemini API 配置正确")
    except Exception as e:
        print(f"   ❌ 失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="news2md - 新闻采集与MD生成")
    parser.add_argument('--crawl', action='store_true', help='仅爬取数据')
    parser.add_argument('--analyze', action='store_true', help='仅分析已有数据')
    parser.add_argument('--test', action='store_true', help='测试API连接')
    parser.add_argument('--json', type=str, help='指定要分析的JSON文件')
    
    args = parser.parse_args()
    
    print("""
╔═══════════════════════════════════════════════════╗
║         🎮 news2md - 新闻采集与MD生成            ║
║                                                   ║
║  Reddit + 3DM 爬取 → Gemini 分析 → 生成 MD 文件  ║
╚═══════════════════════════════════════════════════╝
    """)
    
    try:
        if args.test:
            test_connections()
            return
        
        if args.analyze:
            # 仅分析模式
            if args.json:
                json_path = Path(args.json)
            else:
                json_path = get_output_dir() / "raw_posts.json"
            
            if not json_path.exists():
                print(f"❌ 找不到: {json_path}")
                print("   请先运行爬取，或使用 --json 指定文件")
                return
            
            news_list = analyze(json_path)
            generate(news_list)
            
        elif args.crawl:
            # 仅爬取模式
            crawl()
            
        else:
            # 完整流程
            json_path = crawl()
            news_list = analyze(json_path)
            generate(news_list)
        
        print("\n" + "=" * 50)
        print("🎉 完成！")
        print("=" * 50)
        print("\n📁 生成的文件:")
        print("   • md2video/newsText.md")
        print("   • md2video/audioText.md")
        print("\n🎬 下一步: cd ../md2video && python main.py")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

