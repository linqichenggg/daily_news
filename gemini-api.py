import time
import os
from dotenv import load_dotenv
from google import genai

# 加载环境变量
load_dotenv()

# ========== 配置区域 ==========
# 从环境变量读取API key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("请在环境变量中设置 GEMINI_API_KEY，或者在 config.env 文件中配置")
MODEL = "gemini-2.5-pro"
PROMPT = """
who are you?
"""
# ==============================

def generate_with_stream(client, model, prompt):
    """使用流式响应生成内容，避免长时间思考导致连接断开"""
    print(f"正在等待 {model} 模型响应...")
    print("pro模型需要较长时间思考，请耐心等待（可能需要30-60秒）...\n")
    
    start_time = time.time()
    
    # 使用流式响应保持连接活跃
    response_stream = client.models.generate_content_stream(
        model=model,
        contents=prompt
    )
    
    # 收集响应片段
    full_response = ""
    chunk_count = 0
    
    print("开始接收响应...", end="", flush=True)
    for chunk in response_stream:
        chunk_count += 1
        if hasattr(chunk, 'text') and chunk.text:
            full_response += chunk.text
            print(".", end="", flush=True)
    
    processing_time = time.time() - start_time
    
    print(f"\n\n✅ 响应完成！")
    print(f"处理时间: {processing_time:.2f} 秒 | 响应片段: {chunk_count} 个")
    print("\n" + "=" * 60)
    print(full_response)
    print("=" * 60)
    
    return full_response


# ========== 主程序 ==========
if __name__ == "__main__":
    client = genai.Client(api_key=API_KEY)
    generate_with_stream(client, MODEL, PROMPT)