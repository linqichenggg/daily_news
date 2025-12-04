"""Convert markdown to audio using Minimax TTS."""
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import re
import logging
import json
from datetime import timedelta, date
from pydub import AudioSegment
from dotenv import load_dotenv

# Import Minimax client
from utils.minimax_client import MinimaxTTS, SubtitleGenerator
from utils.paths import get_log_file_path, get_output_dir

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file_path("md2audio")),
        logging.StreamHandler()
    ]
)

def format_time(milliseconds):
    """将毫秒转换为SRT格式的时间字符串 (HH:MM:SS,mmm)"""
    td = timedelta(milliseconds=milliseconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds % 1000:03}"

def generate_silence(duration=1000):
    """生成指定时长的无声音频（默认1秒）"""
    return AudioSegment.silent(duration=duration)  # 确保精确指定毫秒

def preprocess_text(text):
    """预处理文本，处理链接和图片等Markdown元素"""
    logging.debug(f"预处理前的文本: {text[:100]}..." if len(text) > 100 else f"预处理前的文本: {text}")
    
    # 处理类似 S.T.A.L.K.E.R. 这样的缩写（连续的单字母+点），转换为没有点的形式
    # 例如: S.T.A.L.K.E.R. -> STALKER, G.A.M.M.A. -> GAMMA
    def remove_dots_from_acronym(match):
        return match.group(0).replace('.', '')
    text = re.sub(r'(?:[A-Z]\.){2,}[A-Z]?\.?', remove_dots_from_acronym, text)
    logging.debug(f"处理缩写后: {text[:100]}..." if len(text) > 100 else f"处理缩写后: {text}")
    
    # 处理链接 [文本](链接) -> 文本
    # 匹配 Markdown 链接，包括带空格的格式
    text = re.sub(r'\[(.*?)\][ ]*\(.*?\)', r'\1', text)
    logging.debug(f"处理链接后: {text[:100]}..." if len(text) > 100 else f"处理链接后: {text}")
    
    # 处理 Obsidian 格式图片，完全移除 ![[图片.png]]
    text = re.sub(r'!\[\[.*?\]\]', '', text)
    
    # 处理标准 Markdown 格式图片，完全移除 ![alt](url)
    text = re.sub(r'!\[.*?\][ ]*\(.*?\)', '', text)
    logging.debug(f"处理图片后: {text[:100]}..." if len(text) > 100 else f"处理图片后: {text}")
    
    # 将'-'替换为空格
    text = text.replace('-', ' ')
    
    # 将英文双引号转换为中文双引号
    text = text.replace('"', '"').replace('"', '"')
    
    # 处理英文句点，将其转换为中文句号
    text = re.sub(r'([.])(?=\s|$)', '。', text)
    
    # 移除多余空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    logging.debug(f"最终预处理结果: {text[:100]}..." if len(text) > 100 else f"最终预处理结果: {text}")
    
    return text

def sanitize_filename(filename):
    """处理文件名，移除或替换非法字符"""
    # 将引号、空格和其他特殊字符替换为下划线
    filename = re.sub(r'["\'\s\\/:*?"<>|]', '_', filename)
    return filename

def sanitize_title_for_tts(title):
    """清理标题，移除可能导致 TTS 失败的字符"""
    # 处理类似 S.T.A.L.K.E.R. 这样的缩写（连续的单字母+点）
    # 转换为没有点的形式
    title = re.sub(r'\.([A-Z])\.', r'\1', title)  # 移除字母之间的点
    title = re.sub(r'([A-Z])\.([A-Z])', r'\1\2', title)  # 再次处理
    title = re.sub(r'\.+', ' ', title)  # 多个点替换为空格
    title = re.sub(r'\s+', ' ', title).strip()  # 清理多余空格
    return title

def save_timeline(timeline_data, current_date, output_dir):
    """保存时间轴数据到JSON文件"""
    timeline_path = output_dir / f"timeline_{current_date}.json"
    data = {
        "timeline": timeline_data
    }
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"时间轴数据已保存到: {timeline_path}")

def parse_markdown_and_generate_audio(markdown_content):
    """解析Markdown内容，提取标题和文本，生成语音和字幕"""
    logging.info("开始解析Markdown内容")
    
    # 初始化 Minimax
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        logging.error("未找到 MINIMAX_API_KEY 环境变量")
        print("Error: MINIMAX_API_KEY is required in .env file")
        return

    try:
        tts = MinimaxTTS(api_key=api_key)
        subtitle_gen = SubtitleGenerator()
    except Exception as e:
        logging.error(f"Minimax初始化失败: {e}")
        return

    # 初始化时间轴数据
    timeline_data = []
    
    # 获取第一个标题作为主文件名
    first_title_match = re.search(r'##\s+(.*?)(?=\n)', markdown_content)
    if not first_title_match:
        main_title = "未命名文档"
    else:
        main_title = first_title_match.group(1).strip()
    
    logging.info(f"主标题: {main_title}")
    
    # 获取当前日期并创建输出目录
    current_date = date.today().strftime("%Y%m%d")
    output_dir = get_output_dir()  # 使用统一的路径函数
    logging.info(f"输出目录: {output_dir}")
    
    # 使用正则表达式找出所有## 开头的标题及其内容
    sections = re.findall(r'##\s+(.*?)(?=\n##|\Z)', markdown_content, re.DOTALL)
    logging.info(f"找到 {len(sections)} 个章节")
    
    # 生成SRT文件内容
    srt_content = []
    current_time = 0  # 毫秒
    sentence_index = 1
    
    # 创建一个合并的音频文件
    combined_audio = AudioSegment.empty()
    
    # 处理所有章节
    for section_idx, section in enumerate(sections):
        logging.info(f"处理章节 {section_idx+1}/{len(sections)}")
        
        # 分离标题和内容
        lines = section.strip().split('\n')
        title = lines[0].strip()
        logging.info(f"章节标题: {title}")
        
        # 排除标题行，只保留内容
        content = '\n'.join(lines[1:]).strip()
        
        if not content:
            logging.warning(f"章节 '{title}' 没有内容，跳过")
            continue
        
        # 预处理内容
        preprocessed_content = preprocess_text(content)
        logging.info(f"章节预处理后内容: {preprocessed_content[:100]}...")
        
        # 记录章节开始时间
        section_start_time = format_time(current_time)
        
        # 生成临时文件用于Minimax上传
        safe_title = sanitize_filename(title)
        temp_txt_path = output_dir / f"temp_{safe_title}.txt"
        temp_audio_path = output_dir / f"temp_{safe_title}.mp3"
        
        try:
            # 1. 写入临时文本文件
            with open(temp_txt_path, "w", encoding="utf-8") as f:
                f.write(preprocessed_content)
            
            logging.info(f"调用Minimax生成音频: {title}")
            
            # 2. 调用Minimax API
            file_id = tts.upload_file(str(temp_txt_path))
            task_id = tts.submit_tts_task(file_id)
            result_file_id = tts.wait_for_completion(task_id)
            tts.download_file(result_file_id, str(temp_audio_path))
            
            logging.info("Minimax 音频生成完成")
            
            # 3. 读取音频获取准确时长
            audio_segment = AudioSegment.from_file(temp_audio_path)
            audio_duration_ms = len(audio_segment)
            audio_duration_sec = audio_duration_ms / 1000.0
            logging.info(f"音频时长: {audio_duration_ms}ms")
            
            # 4. 生成和校准字幕
            sentences = subtitle_gen.split_text_into_sentences(preprocessed_content)
            estimated_timeline = subtitle_gen.generate_timeline(sentences)
            
            if estimated_timeline:
                estimated_total_sec = estimated_timeline[-1]['end']
                # 计算缩放因子
                scale_factor = audio_duration_sec / estimated_total_sec if estimated_total_sec > 0 else 1.0
                logging.info(f"字幕时间轴缩放因子: {scale_factor:.4f}")
                
                # 生成SRT条目
                for item in estimated_timeline:
                    # 应用缩放并加上当前累计时间
                    start_ms = int(item['start'] * scale_factor * 1000) + current_time
                    end_ms = int(item['end'] * scale_factor * 1000) + current_time
                    
                    # 确保结束时间不超过音频总时长+当前时间
                    # end_ms = min(end_ms, current_time + audio_duration_ms)
                    
                    srt_content.append(f"{sentence_index}\n{format_time(start_ms)} --> {format_time(end_ms)}\n{item['text']}\n")
                    sentence_index += 1
            
            # 5. 合并音频
            combined_audio += audio_segment
            current_time += audio_duration_ms
            
            # 6. 清理临时文件
            if os.path.exists(temp_txt_path):
                os.remove(temp_txt_path)
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            
        except Exception as e:
            logging.error(f"处理章节 '{title}' 时出错: {e}")
            continue
            
        # 章节间隔停顿
        if section_idx < len(sections) - 1:
            silence = generate_silence(1000)
            combined_audio += silence
            current_time += 1000
            logging.debug("章节之间添加停顿: 1000毫秒")
            
        # 记录章节结束时间 (包含停顿)
        section_end_time = format_time(current_time)
        
        # 跳过开场和结束语，不记录到 timeline（它们不需要对应的新闻图片）
        skip_titles = ["单机游戏日报", "开场", "结束", "结束语"]
        if title not in skip_titles:
            timeline_data.append({
                "title": title,
                "start_seconds": section_start_time,
                "end_seconds": section_end_time
            })
    
    # 保存合并的音频文件
    try:
        combined_audio_path = output_dir / f"audio_{current_date}.mp3"
        logging.info(f"保存合并音频文件: {combined_audio_path}")
        combined_audio.export(str(combined_audio_path), format="mp3")
        logging.info("音频文件保存成功")
    except Exception as e:
        logging.error(f"保存合并音频文件时出错: {e}")
    
    # 写入单个SRT文件
    try:
        srt_path = output_dir / f"subtitle_{current_date}.srt"
        logging.info(f"保存字幕文件: {srt_path}")
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            srt_file.write("\n".join(srt_content))
        logging.info("字幕文件保存成功")
    except Exception as e:
        logging.error(f"保存字幕文件时出错: {e}")
    
    # 保存时间轴数据
    save_timeline(timeline_data, current_date, output_dir)
    
    logging.info(f"已生成合并音频文件: {combined_audio_path}")
    logging.info(f"已生成字幕文件: {srt_path}")
    logging.info(f"已生成时间轴文件: {output_dir / f'timeline_{current_date}.json'}")
    
    print(f"已生成合并音频文件: {combined_audio_path}")
    print(f"已生成字幕文件: {srt_path}")
    print(f"已生成时间轴文件: {output_dir / f'timeline_{current_date}.json'}")

def process_markdown_file(file_path):
    """处理Markdown文件"""
    logging.info(f"开始处理Markdown文件: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            markdown_content = file.read()
        logging.info(f"成功读取文件，内容长度: {len(markdown_content)} 字符")
    except Exception as e:
        logging.error(f"读取文件时出错: {e}")
        return
    
    parse_markdown_and_generate_audio(markdown_content)

if __name__ == "__main__":
    # 示例使用
    markdown_file = "./audioText.md"
    
    process_markdown_file(markdown_file)
