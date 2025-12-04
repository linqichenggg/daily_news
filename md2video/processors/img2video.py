"""Convert images to video with timeline support using MoviePy."""
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
import pysrt

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入 MoviePy v2.x
try:
    from moviepy import *
except ImportError:
    print("Error: Please install moviepy (pip install moviepy)")
    sys.exit(1)

# 导入路径工具
from utils.paths import get_log_file_path, get_output_base_dir

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(get_log_file_path("img2video"))
    ]
)
logger = logging.getLogger(__name__)

def time_str_to_seconds(time_str):
    """将字幕格式的时间字符串 (HH:MM:SS,mmm) 转换为秒数"""
    time_str = time_str.replace(',', '.')
    hours, minutes, seconds = time_str.split(':')
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

def create_subtitle_clips(subtitle_file, video_width, video_height):
    """创建字幕片段"""
    if not subtitle_file or not Path(subtitle_file).exists():
        return None

    # 使用 pysrt 解析字幕文件
    try:
        import pysrt
        subs = pysrt.open(str(subtitle_file))
    except ImportError:
        logger.warning("pysrt not installed, trying naive parsing. For better results: pip install pysrt")
        return None

    subtitle_clips = []
    
    # 查找支持中文的系统字体 (MacOS)
    font_path = None
    possible_fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    for p in possible_fonts:
        if Path(p).exists():
            font_path = p
            logger.info(f"使用中文字体: {font_path}")
            break
            
    # 字幕样式配置
    font_size = 56  # 稍微减小字号，确保更多字符能单行显示
    color = 'white'
    stroke_color = 'black'
    stroke_width = 2
    
    # 如果找到中文字体则使用，否则回退
    if font_path:
        font = font_path
    else:
        logger.warning("未找到常用的中文字体文件，字幕可能乱码")
        font = 'Arial'

    # 字幕位置 (底部)
    text_position = ('center', video_height - 150)

    for sub in subs:
        start_time = sub.start.ordinal / 1000.0
        end_time = sub.end.ordinal / 1000.0
        duration = end_time - start_time
        text = sub.text

        if duration <= 0:
            continue

        try:
            # MoviePy v2.x TextClip - 单行模式
            # 不使用 method 参数，默认就是单行渲染
            # 配合字幕拆分（每句最多22字），确保不会换行
            txt_clip = TextClip(
                text=text, 
                font_size=font_size, 
                font=font, 
                color=color, 
                stroke_color=stroke_color, 
                stroke_width=stroke_width
            )
            
            txt_clip = txt_clip.with_start(start_time).with_duration(duration).with_position(text_position)
            subtitle_clips.append(txt_clip)
            
        except Exception as e:
            # 降级尝试：不使用 font 参数，使用默认字体
            try:
                logger.warning(f"无法使用指定字体 {font}，尝试默认字体。错误: {e}")
                txt_clip = TextClip(
                    text=text, 
                    font_size=font_size, 
                    color=color, 
                    stroke_color=stroke_color, 
                    stroke_width=stroke_width
                )
                txt_clip = txt_clip.with_start(start_time).with_duration(duration).with_position(text_position)
                subtitle_clips.append(txt_clip)
            except Exception as e2:
                logger.error(f"创建字幕片段彻底失败: {e2}")
                return None

    return subtitle_clips

def create_news_video(json_path, images_dir, output_name, output_dir, audio_dir="audio"):
    """使用 MoviePy 创建新闻视频"""
    final_output = output_dir / f"video_{output_name}.mp4"
    
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. 准备音频
    audio_path = Path(audio_dir) / f"audio_{output_name}.mp3"
    if not audio_path.exists():
        logger.error(f"音频文件不存在: {audio_path}")
        return False
    
    try:
        audio_clip = AudioFileClip(str(audio_path))
    except Exception as e:
        logger.error(f"加载音频失败: {e}")
        return False

    # 2. 准备视频片段 (图片)
    image_clips = []
    
    # 首先检查是否有目录页 (index.png)，如果有则添加到开头
    index_image_path = Path(images_dir) / "index.png"
    index_duration = 0  # 记录目录页时长，用于调整音频起始时间
    
    if index_image_path.exists():
        # 目录页显示2秒
        index_duration = 2.0
        logger.info(f"找到目录页 index.png，将在开头显示 {index_duration} 秒")
        index_clip = ImageClip(str(index_image_path)).with_duration(index_duration)
        image_clips.append(index_clip)
    
    # 然后处理新闻页面
    news_count = len(data['timeline'])
    logger.info(f"开始处理 {news_count} 个新闻画面片段")
    
    for i in range(news_count):
        news = data['timeline'][i]
        image_path = Path(images_dir) / f"news_{i+1}.png"
        
        if not image_path.exists():
            logger.warning(f"图片不存在: {image_path}")
            continue
            
        # 计算时长
        start_seconds = time_str_to_seconds(news['start_seconds'])
        end_seconds = time_str_to_seconds(news['end_seconds'])
        duration = end_seconds - start_seconds
        
        # 创建图片片段
        img_clip = ImageClip(str(image_path)).with_duration(duration)
        image_clips.append(img_clip)

    if not image_clips:
        logger.error("没有有效的图片片段")
        return False

    # 3. 拼接视频
    video_clip = concatenate_videoclips(image_clips, method="compose")
    
    # 4. 设置音频
    # 如果有目录页，音频需要延迟开始
    if index_duration > 0:
        logger.info(f"音频将延迟 {index_duration} 秒开始播放（目录页期间静音）")
        audio_clip = audio_clip.with_start(index_duration)
    
    # 检查视频时长是否足够
    total_required_duration = index_duration + audio_clip.duration
    if video_clip.duration < total_required_duration:
        diff = total_required_duration - video_clip.duration
        logger.info(f"视频时长不足，延长最后一帧 {diff:.2f} 秒")
        last_clip = image_clips[-1].with_duration(image_clips[-1].duration + diff)
        image_clips[-1] = last_clip
        video_clip = concatenate_videoclips(image_clips, method="compose")
    
    # 合成音频到视频
    video_clip = video_clip.with_audio(audio_clip)
    
    # 5. 添加字幕
    subtitle_path = Path(audio_dir) / f"subtitle_{output_name}.srt"
    subtitle_elements = []
    
    if subtitle_path.exists():
        logger.info("正在生成字幕图层...")
        subtitle_clips = create_subtitle_clips(subtitle_path, video_clip.w, video_clip.h)
        if subtitle_clips:
            # 如果有目录页，字幕也需要延迟
            if index_duration > 0:
                logger.info(f"字幕将延迟 {index_duration} 秒显示")
                subtitle_clips = [clip.with_start(clip.start + index_duration) for clip in subtitle_clips]
            subtitle_elements = subtitle_clips
            logger.info(f"已生成 {len(subtitle_clips)} 条字幕")
        else:
            logger.warning("字幕生成失败或跳过")
    
    # 6. 合成最终视频
    logger.info("正在合成最终视频 (这可能需要一点时间)...")
    
    final_clip = CompositeVideoClip([video_clip] + subtitle_elements)
    
    try:
        final_clip.write_videofile(
            str(final_output),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium', 
            threads=4,
            logger=None 
        )
        logger.info(f"✅ 视频生成成功: {final_output}")
        return True
        
    except Exception as e:
        logger.error(f"写入视频文件失败: {e}")
        return False
    finally:
        try:
            video_clip.close()
            audio_clip.close()
            final_clip.close()
        except:
            pass

async def main():
    """主函数"""
    output_dir = get_output_base_dir()
    
    date_dirs = sorted([d for d in output_dir.glob("*") if d.is_dir() and d.name.isdigit()], 
                      reverse=True)
    
    if not date_dirs:
        return False
        
    latest_dir = date_dirs[0]
    logger.info(f"使用最新日期目录: {latest_dir}")
    
    json_files = list(latest_dir.glob("*.json"))
    if not json_files:
        return False
        
    json_path = json_files[0]
    images_dir = latest_dir / "images"
    output_name = latest_dir.name
    
    # 检查是否安装了 pysrt
    try:
        import pysrt
    except ImportError:
        import subprocess
        logger.info("正在安装 pysrt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pysrt"])
    
    return create_news_video(json_path, images_dir, output_name, 
                        output_dir=latest_dir,
                        audio_dir=str(latest_dir))

if __name__ == "__main__":
    import asyncio
    try:
        success = asyncio.run(main())
    except Exception as e:
        success = main()
    sys.exit(0 if success else 1)
