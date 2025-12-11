"""
3DM新闻爬虫 - 使用 requests + BeautifulSoup 爬取3DM单机游戏新闻
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import re

from .base import BaseCrawler, NewsPost


class DM3Crawler(BaseCrawler):
    """3DM单机游戏新闻爬虫"""
    
    # 单机资讯页面URL
    NEWS_URL = "https://www.3dmgame.com/news_32_1/"
    
    # 最多收集多少条新闻
    MAX_POSTS = 30
    
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __init__(self, config: dict = None):
        """初始化爬虫"""
        super().__init__("3DM")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Referer': 'https://www.3dmgame.com/',
        })
    
    def test_connection(self) -> bool:
        """测试3DM网站连接"""
        try:
            response = self.session.get(self.NEWS_URL, timeout=10)
            if response.status_code == 200:
                print("✅ 3DM 连接成功！")
                return True
            else:
                print(f"❌ 3DM 连接失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 3DM 连接失败: {e}")
            return False
    
    def crawl(self) -> List[NewsPost]:
        """爬取3DM单机游戏新闻（从最新开始，最多30条）"""
        print("🔹 开始爬取3DM单机游戏新闻...")
        posts = []
        
        try:
            # 添加时间戳参数绕过 CDN 缓存
            import time
            cache_bust = f"?_t={int(time.time())}"
            response = self.session.get(self.NEWS_URL + cache_bust, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有新闻条目（HTML中已按时间倒序，最新在前）
            news_items = soup.find_all('li', class_='selectpost')
            print(f"   页面共 {len(news_items)} 条新闻")
            
            # 从最新开始，最多取 MAX_POSTS 条
            for item in news_items[:self.MAX_POSTS]:
                try:
                    post = self._parse_news_item(item)
                    if post:
                        posts.append(post)
                        # 打印第一条新闻的时间，验证是否从最新开始
                        if len(posts) == 1:
                            print(f"   最新新闻: {post.title[30]}... ({post.published_at})")
                except Exception as e:
                    print(f"   ⚠️ 解析新闻条目失败: {e}")
                    continue
            
            print(f"   ✅ 3DM爬取完成，获取 {len(posts)} 条新闻")
            
        except requests.RequestException as e:
            print(f"   ❌ 请求3DM失败: {e}")
        except Exception as e:
            print(f"   ❌ 爬取3DM出错: {e}")
        
        return posts
    
    def _parse_news_item(self, item) -> NewsPost:
        """解析单条新闻"""
        # 获取标题和链接
        title_tag = item.find('a', class_='bt')
        if not title_tag:
            return None
        
        title = title_tag.get_text(strip=True)
        url = title_tag.get('href', '')
        
        # 获取时间
        time_tag = item.find('span', class_='time')
        published_at = datetime.now()
        if time_tag:
            time_str = time_tag.get_text(strip=True)
            try:
                # 格式: 2025-12-04 09:34:07
                published_at = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        # 获取描述
        desc_tag = item.find('div', class_='miaoshu')
        content = ""
        if desc_tag:
            content = desc_tag.get_text(strip=True)
            # 清理HTML实体
            content = self._clean_content(content)
        
        # 获取游戏标签
        game_tag = item.find('div', class_='bq')
        game_name = ""
        if game_tag:
            game_link = game_tag.find('a', class_='a')
            if game_link:
                game_name = game_link.get_text(strip=True)
        
        return NewsPost(
            title=title,
            content=content,
            url=url,
            published_at=published_at.isoformat(),
            subreddit=f"3DM/{game_name}" if game_name else "3DM"
        )
    
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        # 移除多余空白
        content = re.sub(r'\s+', ' ', content).strip()
        # 移除HTML实体残留
        content = content.replace('&nbsp;', ' ')
        # 限制长度
        return content[:1000] if len(content) > 1000 else content
    
    def _is_recent(self, pub_time: datetime, hours: int = 48) -> bool:
        """检查是否是最近的新闻（默认48小时内）"""
        if not pub_time:
            return True
        now = datetime.now()
        cutoff = now - timedelta(hours=hours)
        return pub_time >= cutoff

