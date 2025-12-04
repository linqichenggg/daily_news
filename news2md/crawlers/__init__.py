"""爬虫子模块"""
from .base import BaseCrawler, NewsPost
from .reddit import RedditCrawler
from .dm3 import DM3Crawler

__all__ = ['BaseCrawler', 'NewsPost', 'RedditCrawler', 'DM3Crawler']

