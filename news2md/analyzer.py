"""
新闻分析器 - 使用 Gemini API 分析和筛选游戏新闻
"""
import os
import json
import time
import re
from typing import List, Dict
from pathlib import Path
import yaml
from google import genai


class NewsAnalyzer:
    """使用 Gemini 分析游戏新闻"""
    
    SYSTEM_PROMPT = """从帖子中提取游戏新闻，返回JSON数组：
[{"title":"标题15字内","summary":"详细摘要100字以内，尽可能详细介绍，包含背景细节","audio_text":"播报3-5句话，简单介绍即可","original_url":"链接"}]
要求：中文、直接陈述、只返回JSON"""

    def __init__(self, config: dict = None):
        """初始化分析器"""
        self.config = config or self._load_default_config()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ 请设置环境变量 GEMINI_API_KEY")
        
        self.model = self.config.get('model', 'gemini-2.5-flash')
        self.max_news = self.config.get('max_news', 5)
        
        # 初始化客户端（保持简单，和 gemini-api.py 一致）
        self.client = genai.Client(api_key=api_key)
    
    def _load_default_config(self) -> dict:
        """加载默认配置"""
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
        return full_config.get('gemini', {})
    
    def _format_posts(self, posts: List[Dict]) -> str:
        """格式化帖子数据用于分析"""
        formatted = []
        for i, post in enumerate(posts, 1):
            formatted.append(f"""
--- 帖子 {i} ---
标题: {post.get('title', '')}
内容: {post.get('content', '')[:500]}
来源: r/{post.get('subreddit', '')}
链接: {post.get('url', '')}
""")
        return "\n".join(formatted)
    
    def analyze(self, posts: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        分批分析帖子并提取新闻
        
        Args:
            posts: 帖子列表 (dict 格式)
            batch_size: 每批处理的帖子数量
            
        Returns:
            提取的新闻列表（整合所有批次）
        """
        if not posts:
            print("⚠️ 没有帖子需要分析")
            return []
        
        # 计算批次数量
        total_posts = len(posts)
        num_batches = (total_posts + batch_size - 1) // batch_size
        
        print(f"\n🤖 使用 {self.model} 分批分析 {total_posts} 条帖子")
        print(f"   📦 每批 {batch_size} 条，共 {num_batches} 批")
        print(f"   💡 流式响应会实时显示进度\n")
        
        all_news = []
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_posts)
            batch_posts = posts[start_idx:end_idx]
            
            print(f"\n{'='*50}")
            print(f"📦 批次 {batch_idx + 1}/{num_batches}：帖子 {start_idx + 1}-{end_idx}")
            print(f"{'='*50}")
            
            batch_news = self._analyze_batch(batch_posts, batch_idx + 1, num_batches)
            all_news.extend(batch_news)
            
            print(f"   ✅ 本批提取 {len(batch_news)} 条新闻")
            
            # 批次间休息，避免 API 限流
            if batch_idx < num_batches - 1:
                print(f"   ⏳ 等待 2 秒后处理下一批...")
                time.sleep(2)
        
        print(f"\n{'='*50}")
        print(f"🎉 全部完成！共提取 {len(all_news)} 条新闻")
        print(f"{'='*50}")
        
        return all_news
    
    def _analyze_batch(self, posts: List[Dict], batch_num: int, total_batches: int, max_retries: int = 3) -> List[Dict]:
        """
        分析单批帖子（带重试机制）
        
        Args:
            posts: 帖子列表
            batch_num: 当前批次号
            total_batches: 总批次数
            max_retries: 最大重试次数
        """
        posts_text = self._format_posts(posts)
        
        # 每批最多提取的新闻数（根据批次数量分配）
        news_per_batch = max(2, self.max_news // total_batches + 1)
        
        full_prompt = f"""{self.SYSTEM_PROMPT}

---

请从以下 {len(posts)} 条帖子中，筛选出最多 {news_per_batch} 条最有价值的单机游戏新闻：

{posts_text}

请返回 JSON 格式的新闻列表。"""

        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                if attempt > 0:
                    print(f"   🔄 重试 {attempt}/{max_retries}...")
                    time.sleep(3)  # 重试前等待 3 秒
                
                # 使用流式响应
                response_stream = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=full_prompt
                )
                
                full_response = ""
                
                print("   📥 接收响应: ", end="", flush=True)
                
                for chunk in response_stream:
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        print(".", end="", flush=True)
                
                processing_time = time.time() - start_time
                print(f" 完成 ({processing_time:.1f}秒)")
                
                # 解析 JSON
                return self._parse_json(full_response)
                
            except Exception as e:
                print(f" ❌ 失败")
                print(f"   错误: {type(e).__name__}: {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    print(f"   ⏳ 等待 5 秒后重试批次 {batch_num}...")
                    time.sleep(5)
                else:
                    print(f"   ⚠️ 批次 {batch_num} 已达最大重试次数，跳过")
                    return []  # 返回空列表，不影响其他批次
        
        return []
    
    def _parse_json(self, response: str) -> List[Dict]:
        """解析 JSON 响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            print(f"⚠️ 无法解析 JSON 响应")
            return []

