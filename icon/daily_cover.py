#!/usr/bin/env python3
"""
AI 早报封面生成器 (报纸风格)
功能: 生成复古报纸质感的早报封面

布局:
┌─────────────────────────────────────────────────────┐
│  ═══════════════════════════════════════════════    │
│                    AI 早报                           │
│            ARTIFICIAL INTELLIGENCE DAILY             │
│  ═══════════════════════════════════════════════    │
│  ─────────────────────────────────────────────────  │
│  Vol.XXX    |    Tuesday, November 25, 2025         │
│  ─────────────────────────────────────────────────  │
│                                                     │
│     ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│     │ icon │  │ icon │  │ icon │  │ icon │         │
│     └──────┘  └──────┘  └──────┘  └──────┘         │
│                                                     │
│  ─────────────────────────────────────────────────  │
│           "Today's Top AI Headlines"                │
│  ═══════════════════════════════════════════════    │
└─────────────────────────────────────────────────────┘

使用方法:
    python daily_cover.py -k openai google apple
    python daily_cover.py -k openai anthropic -d "2025.11.25"
    python daily_cover.py -k gpt claude -o my_cover.png
"""

import os
import sys
import datetime
import argparse
import random
from pathlib import Path
from io import BytesIO
import requests

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("请先安装 Pillow: pip install Pillow")
    sys.exit(1)


class LobeIconsDownloader:
    """Lobe Icons 下载器 - 支持关键词智能匹配"""
    
    CDN_BASE_URL = "https://unpkg.com/@lobehub/icons-static-png@latest"
    
    # 关键词到图标的映射（支持模糊匹配）
    KEYWORD_MAPPING = {
        "openai": ["gpt", "chatgpt", "sora", "o1", "4o", "gpt4", "gpt5"],
        "anthropic": ["claude", "sonnet", "opus", "haiku"],
        "google": ["gemini", "gemma", "bard", "谷歌"],
        "meta": ["llama", "facebook", "instagram", "meta"],
        "microsoft": ["copilot", "bing", "azure", "微软"],
        "apple": ["apple", "siri", "iphone", "苹果"],
        "nvidia": ["nvidia", "h100", "rtx", "英伟达"],
        "midjourney": ["mj", "midjourney", "画图"],
        "stability": ["sd", "stable", "diffusion", "sdxl"],
        "huggingface": ["hf", "hugging", "transformers"],
        "github": ["git", "代码", "开源"],
        "twitter": ["x", "twitter", "推特"],
        "tiktok": ["douyin", "tiktok", "抖音"],
        "deepseek": ["deepseek", "深度求索"],
        "alibaba": ["qwen", "通义", "阿里"],
        "baidu": ["wenxin", "文心", "百度", "ernie"],
        "tencent": ["hunyuan", "混元", "腾讯"],
        "bytedance": ["doubao", "豆包", "字节"],
        "zhipu": ["glm", "chatglm", "智谱"],
        "moonshot": ["kimi", "月之暗面"],
        "minimax": ["minimax", "海螺"],
        "perplexity": ["perplexity", "pplx"],
        "cohere": ["cohere", "command"],
        "mistral": ["mistral", "mixtral"],
        "runway": ["runway", "gen2", "gen3"],
    }

    def __init__(self, cache_dir=None):
        self.cache_dir = Path(cache_dir or Path(__file__).parent / "icons_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def match_slug(self, keyword):
        """根据关键词匹配图标 slug"""
        keyword = keyword.lower().strip()
        
        if keyword in self.KEYWORD_MAPPING:
            return keyword
        
        for slug, tags in self.KEYWORD_MAPPING.items():
            if keyword in tags or any(keyword in tag for tag in tags):
                print(f"  🔗 {keyword} → {slug}")
                return slug
        
        return keyword

    def download_icon(self, keyword):
        """下载图标（优先彩色，回退黑白）"""
        slug = self.match_slug(keyword)
        
        variants = [
            (f"{slug}-color", "color", "彩色"),
            (slug, "mono", "黑白"),
        ]
        
        for filename, cache_suffix, label in variants:
            cache_path = self.cache_dir / f"{slug}_{cache_suffix}.png"
            
            if cache_path.exists():
                print(f"  📦 缓存加载: {slug} ({label})")
                return Image.open(cache_path)
            
            url = f"{self.CDN_BASE_URL}/light/{filename}.png"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    with open(cache_path, 'wb') as f:
                        f.write(resp.content)
                    print(f"  🌐 下载成功: {slug} ({label})")
                    return Image.open(BytesIO(resp.content))
            except Exception:
                continue
        
        print(f"  ⚠️ 图标未找到: {slug}")
        return None


class NewspaperCoverGenerator:
    """报纸风格封面生成器"""
    
    # 报纸配色方案
    PAPER_COLORS = {
        "classic": {
            "bg": (252, 249, 242),        # 米黄纸张
            "text": (35, 31, 32),          # 深墨色
            "accent": (139, 69, 19),       # 棕褐色
            "line": (180, 170, 155),       # 浅灰线条
        },
        "sepia": {
            "bg": (245, 235, 220),         # 泛黄纸张
            "text": (60, 40, 30),          # 深棕色
            "accent": (160, 82, 45),       # 赭石色
            "line": (200, 180, 160),
        },
        "modern": {
            "bg": (250, 250, 248),         # 白纸
            "text": (25, 25, 25),          # 纯黑
            "accent": (180, 40, 40),       # 红色点缀
            "line": (200, 200, 200),
        },
        "vintage": {
            "bg": (240, 230, 210),         # 老报纸
            "text": (50, 40, 35),          
            "accent": (120, 60, 30),       
            "line": (190, 175, 150),
        },
    }

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.downloader = LobeIconsDownloader()
        self.margin = 60

    def _get_font(self, size, bold=False, serif=True):
        """获取字体"""
        if serif:
            # 衬线字体（报纸标题风格）
            font_paths = [
                "/System/Library/Fonts/Times.ttc",
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                "/Library/Fonts/Georgia.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "C:/Windows/Fonts/times.ttf",
                "C:/Windows/Fonts/georgia.ttf",
            ]
        else:
            # 无衬线字体
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
        
        return ImageFont.load_default()

    def _get_chinese_font(self, size):
        """获取中文字体"""
        font_paths = [
            "/System/Library/Fonts/STSong.ttf",           # 宋体
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/Library/Fonts/Songti.ttc",
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
        
        return self._get_font(size, serif=True)

    def _draw_paper_texture(self, img, colors):
        """添加纸张纹理"""
        # 添加轻微噪点
        pixels = img.load()
        bg = colors["bg"]
        
        for y in range(self.height):
            for x in range(self.width):
                # 随机微小变化
                noise = random.randint(-8, 8)
                r = max(0, min(255, bg[0] + noise))
                g = max(0, min(255, bg[1] + noise))
                b = max(0, min(255, bg[2] + noise))
                pixels[x, y] = (r, g, b)
        
        return img

    def _draw_decorative_lines(self, draw, colors, y_positions):
        """绘制装饰线条"""
        line_color = colors["line"]
        accent = colors["accent"]
        
        for y, style in y_positions:
            if style == "double":
                # 双线
                draw.line([(self.margin, y), (self.width - self.margin, y)], 
                         fill=line_color, width=2)
                draw.line([(self.margin, y + 6), (self.width - self.margin, y + 6)], 
                         fill=line_color, width=1)
            elif style == "thick":
                # 粗线
                draw.line([(self.margin, y), (self.width - self.margin, y)], 
                         fill=accent, width=4)
            elif style == "thin":
                # 细线
                draw.line([(self.margin, y), (self.width - self.margin, y)], 
                         fill=line_color, width=1)
            elif style == "dotted":
                # 点线
                for x in range(self.margin, self.width - self.margin, 8):
                    draw.ellipse([x, y, x+2, y+2], fill=line_color)

    def _draw_masthead(self, draw, colors, date_str, vol_num, author=None):
        """绘制报头"""
        text_color = colors["text"]
        accent = colors["accent"]
        
        # 顶部装饰线
        draw.line([(self.margin, 40), (self.width - self.margin, 40)], 
                 fill=accent, width=3)
        draw.line([(self.margin, 46), (self.width - self.margin, 46)], 
                 fill=text_color, width=1)
        
        # 主标题 "AI 早报"
        title_font = self._get_chinese_font(90)
        title = "AI 早报"
        bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = bbox[2] - bbox[0]
        title_x = (self.width - title_width) // 2
        draw.text((title_x, 60), title, font=title_font, fill=text_color)
        
        # 英文副标题
        subtitle_font = self._get_font(28, serif=True)
        subtitle = "ARTIFICIAL INTELLIGENCE DAILY"
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = bbox[2] - bbox[0]
        subtitle_x = (self.width - subtitle_width) // 2
        draw.text((subtitle_x, 165), subtitle, font=subtitle_font, fill=accent)
        
        # 分隔线
        draw.line([(self.margin, 200), (self.width - self.margin, 200)], 
                 fill=text_color, width=2)
        draw.line([(self.margin, 206), (self.width - self.margin, 206)], 
                 fill=text_color, width=1)
        
        # 期数和日期行
        info_font = self._get_font(24, serif=True)
        
        # 左侧：期数
        vol_text = f"Vol. {vol_num}"
        draw.text((self.margin + 10, 218), vol_text, font=info_font, fill=text_color)
        
        # 中间：作者信息
        if author:
            author_text = f"Made by {author}"
        else:
            author_text = "|"
        
        author_bbox = draw.textbbox((0, 0), author_text, font=info_font)
        author_width = author_bbox[2] - author_bbox[0]
        author_x = (self.width - author_width) // 2
        draw.text((author_x, 218), author_text, font=info_font, fill=accent)
        
        # 右侧：日期
        date_bbox = draw.textbbox((0, 0), date_str, font=info_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text((self.width - self.margin - date_width - 10, 218), 
                 date_str, font=info_font, fill=text_color)
        
        # 底部细线
        draw.line([(self.margin, 248), (self.width - self.margin, 248)], 
                 fill=colors["line"], width=1)

    def _draw_icons_row(self, img, keywords, colors, y_center):
        """绘制图标行"""
        icons = []
        print("📥 下载图标...")
        
        for kw in keywords[:4]:
            icon = self.downloader.download_icon(kw)
            if icon:
                icons.append(icon)
        
        if not icons:
            return
        
        icon_size = 120
        spacing = 40
        total_width = len(icons) * icon_size + (len(icons) - 1) * spacing
        start_x = (self.width - total_width) // 2
        
        for i, icon in enumerate(icons):
            x = start_x + i * (icon_size + spacing)
            y = y_center - icon_size // 2
            
            # 创建方形边框背景
            frame = Image.new("RGBA", (icon_size + 16, icon_size + 16), (0, 0, 0, 0))
            frame_draw = ImageDraw.Draw(frame)
            
            # 绘制边框
            frame_draw.rectangle(
                [0, 0, icon_size + 15, icon_size + 15],
                outline=colors["line"],
                width=2
            )
            
            # 内部白色背景
            frame_draw.rectangle(
                [4, 4, icon_size + 11, icon_size + 11],
                fill=(255, 255, 255, 255)
            )
            
            # 缩放图标
            icon_resized = icon.resize((icon_size - 16, icon_size - 16), Image.Resampling.LANCZOS)
            if icon_resized.mode != "RGBA":
                icon_resized = icon_resized.convert("RGBA")
            
            # 粘贴图标
            frame.paste(icon_resized, (12, 12), icon_resized)
            
            # 粘贴到主图
            img.paste(frame, (x - 8, y - 8), frame)

    def _draw_footer(self, draw, colors, tagline):
        """绘制页脚"""
        text_color = colors["text"]
        accent = colors["accent"]
        
        # 上方装饰线
        draw.line([(self.margin, self.height - 100), 
                  (self.width - self.margin, self.height - 100)], 
                 fill=colors["line"], width=1)
        
        # 标语
        tagline_font = self._get_font(28, serif=True)
        bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_width = bbox[2] - bbox[0]
        tagline_x = (self.width - tagline_width) // 2
        
        # 引号装饰
        quote_font = self._get_font(36, serif=True)
        draw.text((tagline_x - 25, self.height - 82), "\"", font=quote_font, fill=accent)
        draw.text((tagline_x + tagline_width + 8, self.height - 82), "\"", font=quote_font, fill=accent)
        
        draw.text((tagline_x, self.height - 75), tagline, font=tagline_font, fill=text_color)
        
        # 底部双线
        draw.line([(self.margin, self.height - 40), 
                  (self.width - self.margin, self.height - 40)], 
                 fill=text_color, width=1)
        draw.line([(self.margin, self.height - 34), 
                  (self.width - self.margin, self.height - 34)], 
                 fill=accent, width=3)

    def generate(self, keywords, date_str=None, style="classic", output="brief.png",
                 tagline="Today's Top AI Headlines", vol_num=None, author=None):
        """
        生成报纸风格封面
        
        Args:
            keywords: 关键词列表
            date_str: 日期字符串
            style: 配色风格 (classic/sepia/modern/vintage)
            output: 输出文件路径
            tagline: 底部标语
            vol_num: 期数（默认根据日期自动计算）
            author: 作者名称（如 "lqc"）
        """
        print(f"\n📰 生成报纸风格封面...")
        print(f"  风格: {style}")
        print(f"  关键词: {keywords}")
        
        colors = self.PAPER_COLORS.get(style, self.PAPER_COLORS["classic"])
        
        # 1. 创建纸张背景
        img = Image.new("RGB", (self.width, self.height), colors["bg"])
        img = self._draw_paper_texture(img, colors)
        draw = ImageDraw.Draw(img)
        
        # 2. 处理日期
        if date_str is None:
            now = datetime.datetime.now()
            # 英文日期格式
            date_str = now.strftime("%A, %B %d, %Y")
        
        # 计算期数（从2024年1月1日开始）
        if vol_num is None:
            base_date = datetime.datetime(2024, 1, 1)
            today = datetime.datetime.now()
            vol_num = (today - base_date).days + 1
        
        # 3. 绘制报头
        self._draw_masthead(draw, colors, date_str, vol_num, author)
        
        # 4. 绘制图标区域
        self._draw_icons_row(img, keywords, colors, y_center=420)
        
        # 5. 绘制页脚
        self._draw_footer(draw, colors, tagline)
        
        # 6. 保存
        img.save(output, "PNG", quality=95)
        print(f"\n✅ 封面已生成: {output}")
        
        return output


def main():
    parser = argparse.ArgumentParser(
        description="AI 早报封面生成器 (报纸风格)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python daily_cover.py -k openai google apple
  python daily_cover.py -k gpt claude gemini deepseek -s sepia
  python daily_cover.py -k openai -d "Monday, November 25, 2025" -o my_cover.png
  
可用风格: classic, sepia, modern, vintage

关键词支持智能匹配，例如:
  gpt → openai
  claude → anthropic
  gemini → google
  kimi → moonshot
        """
    )
    
    parser.add_argument("-k", "--keywords", nargs="+", required=True,
                        help="新闻关键词 (如: openai google apple)")
    parser.add_argument("-d", "--date", help="日期字符串")
    parser.add_argument("-s", "--style", default="classic",
                        choices=["classic", "sepia", "modern", "vintage"],
                        help="配色风格 (默认: classic)")
    parser.add_argument("-o", "--output", default="brief.png", help="输出文件路径")
    parser.add_argument("--tagline", default="Today's Top AI Headlines", 
                        help="底部标语")
    parser.add_argument("--vol", type=int, help="期数")
    parser.add_argument("--author", help="作者名称 (如: lqc)")
    parser.add_argument("--width", type=int, default=1280, help="宽度")
    parser.add_argument("--height", type=int, default=720, help="高度")
    
    args = parser.parse_args()

    gen = NewspaperCoverGenerator(width=args.width, height=args.height)
    gen.generate(
        keywords=args.keywords,
        date_str=args.date,
        style=args.style,
        output=args.output,
        tagline=args.tagline,
        vol_num=args.vol,
        author=args.author
    )


if __name__ == "__main__":
    main()
