"""
Reddit 爬虫 - 使用 RSS Feed 获取游戏新闻（无需 API Key）
"""
import re
import html
from datetime import datetime, timezone
from typing import List
from pathlib import Path
import yaml
import feedparser

from .base import BaseCrawler, NewsPost


class RedditCrawler(BaseCrawler):
    """Reddit RSS 爬虫"""
    
    RSS_BASE_URL = "https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit=3"
    USER_AGENT = "DailyGamingNewsBot/1.0"
    
    def __init__(self, config: dict = None):
        super().__init__("reddit")
        self.config = config or self._load_default_config()
    
    def _load_default_config(self) -> dict:
        """加载默认配置"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
        return full_config.get('reddit', {})
    
    def test_connection(self) -> bool:
        """测试 RSS 连接"""
        try:
            test_url = self.RSS_BASE_URL.format(subreddit="Games")
            feed = feedparser.parse(test_url, agent=self.USER_AGENT)
            
            if feed.status == 200 and len(feed.entries) > 0:
                print("✅ Reddit RSS 连接成功！")
                return True
            elif feed.status == 403:
                print("❌ Reddit 返回 403，可能是 IP 被限制")
                return False
            else:
                print(f"❌ Reddit RSS 连接失败，状态码: {feed.status}")
                return False
        except Exception as e:
            print(f"❌ Reddit RSS 连接失败: {e}")
            return False
    
    def _parse_published_time(self, entry) -> datetime:
        """解析发布时间"""
        # feedparser 会把时间解析到 published_parsed (time.struct_time)
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            from time import mktime
            return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
        
        # 备用：直接解析字符串
        if hasattr(entry, 'published'):
            try:
                # Reddit RSS 时间格式示例: "2024-12-03T10:30:00+00:00"
                return datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
            except:
                pass
        
        # 默认返回当前时间
        return datetime.now(timezone.utc)
    
    def _is_recent(self, pub_time: datetime, hours: int = 48) -> bool:
        """检查是否是近期的帖子（默认48小时内）"""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        return pub_time >= cutoff
    
    def _extract_content(self, entry) -> str:
        """从 RSS entry 提取内容"""
        content = ""
        
        # 尝试获取内容
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].get('value', '')
        elif hasattr(entry, 'summary'):
            content = entry.summary or ''
        
        # 解码 HTML 实体 (&#32; -> 空格, &quot; -> 引号 等)
        content = html.unescape(content)
        
        # 清理 HTML 标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理 "submitted by /u/xxx [link] [comments]" 这类固定文本
        content = re.sub(r'submitted by\s+/u/\S+\s*\[link\]\s*\[comments\]', '', content)
        
        # 清理多余空白
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content[:1000] if content else ""  # 限制长度
    
    def _extract_subreddit(self, entry) -> str:
        """从 entry 提取 subreddit 名称"""
        # 从 link 中提取: https://www.reddit.com/r/Games/comments/...
        if hasattr(entry, 'link'):
            match = re.search(r'/r/([^/]+)/', entry.link)
            if match:
                return match.group(1)
        return "unknown"
    
    def _to_news_post(self, entry, subreddit: str) -> NewsPost:
        """将 RSS entry 转换为 NewsPost"""
        pub_time = self._parse_published_time(entry)
        
        # 解码标题中的 HTML 实体
        title = html.unescape(entry.title) if hasattr(entry, 'title') else "无标题"
        
        return NewsPost(
            title=title,
            content=self._extract_content(entry),
            url=entry.link if hasattr(entry, 'link') else "",
            published_at=pub_time.isoformat(),
            subreddit=subreddit
        )
    
    def crawl_subreddit(self, subreddit_name: str) -> List[NewsPost]:
        """爬取单个 subreddit"""
        posts = []
        url = self.RSS_BASE_URL.format(subreddit=subreddit_name)
        
        try:
            feed = feedparser.parse(url, agent=self.USER_AGENT)
            
            if feed.status != 200:
                print(f"  ⚠️ r/{subreddit_name}: 状态码 {feed.status}")
                return posts
            
            for entry in feed.entries:
                pub_time = self._parse_published_time(entry)
                
                # 只保留48小时内的帖子
                if not self._is_recent(pub_time, hours=48):
                    continue
                
                posts.append(self._to_news_post(entry, subreddit_name))
            
            print(f"  📰 r/{subreddit_name}: 获取 {len(posts)} 条帖子")
            
        except Exception as e:
            print(f"  ⚠️ r/{subreddit_name} 爬取失败: {e}")
        
        return posts
    
    def crawl(self) -> List[NewsPost]:
        """爬取所有配置的 subreddit"""
        all_posts = []
        subreddits = self.config.get('subreddits', ['Games'])
        
        print(f"\n🚀 开始爬取 Reddit RSS，共 {len(subreddits)} 个 subreddit...")
        print(f"   筛选条件: /top?t=day (48小时内发布)")
        
        for subreddit_name in subreddits:
            posts = self.crawl_subreddit(subreddit_name)
            all_posts.extend(posts)
        
        # 去重（同一帖子可能出现在多个 subreddit）
        seen_urls = set()
        unique_posts = []
        for post in all_posts:
            if post.url not in seen_urls:
                seen_urls.add(post.url)
                unique_posts.append(post)
        
        print(f"\n✅ 爬取完成！共获取 {len(unique_posts)} 条帖子")
        return unique_posts
