"""
爬虫基类 - 定义统一的数据格式和接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
import json
from pathlib import Path


@dataclass
class NewsPost:
    """统一的帖子数据格式（精简版）"""
    title: str                      # 标题
    content: str                    # 内容
    url: str                        # 原文链接
    published_at: str               # 发布时间 (ISO格式)
    subreddit: str = ""             # 来源版块
    
    def to_dict(self) -> dict:
        return asdict(self)


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.crawled_at = datetime.now().isoformat()
    
    @abstractmethod
    def crawl(self) -> List[NewsPost]:
        """执行爬取，返回帖子列表"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试API连接是否正常"""
        pass
    
    def save_to_json(self, posts: List[NewsPost], filepath: Path) -> None:
        """保存数据到JSON文件"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "source": self.name,
            "crawled_at": self.crawled_at,
            "count": len(posts),
            "posts": [post.to_dict() for post in posts]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存 {len(posts)} 条数据到 {filepath}")

