"""
Markdown 生成器 - 生成 newsText.md 和 audioText.md
输出到 news2md/output/日期/ 目录，不影响 md2video
"""
from datetime import datetime
from typing import List, Dict
from pathlib import Path


class MarkdownGenerator:
    """生成 MD 文件（输出到 news2md/output 目录）"""
    
    def __init__(self, output_dir: Path = None):
        """
        初始化生成器
        
        Args:
            output_dir: 输出目录，默认为 news2md/output/当天日期/
        """
        if output_dir:
            self.output_dir = output_dir
        else:
            # 默认输出到 news2md/output/日期/ 目录
            today = datetime.now().strftime("%Y%m%d")
            self.output_dir = Path(__file__).parent / "output" / today
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_news_text(self, news_list: List[Dict]) -> str:
        """
        生成 newsText.md 内容
        
        格式:
        ## 新闻标题
        新闻摘要
        """
        lines = []
        for news in news_list:
            title = news.get('title', '无标题')
            summary = news.get('summary', '')
            lines.append(f"## {title}")
            lines.append(summary)
            lines.append("")
        return "\n".join(lines)
    
    def generate_audio_text(self, news_list: List[Dict]) -> str:
        """
        生成 audioText.md 内容
        
        格式（每条新闻单独一个章节，用于 TTS 分段）:
        ## 新闻标题1
        欢迎收看今天的单机游戏日报。新闻1播报文本
        
        ## 新闻标题2
        新闻2播报文本
        
        ## 结束
        结束语
        """
        lines = []
        
        # 每条新闻单独一个章节
        for i, news in enumerate(news_list):
            title = news.get('title', '游戏资讯')
            audio_text = news.get('audio_text') or news.get('summary', '')
            if audio_text:
                lines.append(f"## {title}")
                # 第一条新闻前加开场白
                if i == 0:
                    lines.append(f"欢迎收看今天的单机游戏日报。{audio_text}")
                else:
                    lines.append(audio_text)
                lines.append("")
        
        # 结束语（单独章节）
        lines.append("## 结束")
        lines.append("今天的单机游戏资讯就到这里，感谢收看。")
        lines.append("")
        
        return "\n".join(lines)
    
    def save(self, news_list: List[Dict]) -> Dict[str, Path]:
        """
        保存 MD 文件到 news2md/output/日期/ 目录
        
        Args:
            news_list: 新闻列表
            
        Returns:
            生成的文件路径
        """
        news_text_path = self.output_dir / "newsText.md"
        audio_text_path = self.output_dir / "audioText.md"
        
        # 生成并保存
        news_content = self.generate_news_text(news_list)
        audio_content = self.generate_audio_text(news_list)
        
        news_text_path.write_text(news_content, encoding='utf-8')
        print(f"✅ 已生成 {news_text_path}")
        
        audio_text_path.write_text(audio_content, encoding='utf-8')
        print(f"✅ 已生成 {audio_text_path}")
        
        return {
            "news_text": news_text_path,
            "audio_text": audio_text_path
        }
