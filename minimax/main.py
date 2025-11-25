#!/usr/bin/env python3
"""
语音合成完整工作流
使用 Minimax API 将文本转换为语音

使用方法:
1. 配置设置 (推荐使用配置文件):
   - 复制 config.env 为 .env
   - 编辑 .env 文件，设置所需参数

2. 或者使用环境变量 (临时设置):
   - export MINIMAX_API_KEY="your_key"
   - export INPUT_FILE_PATH="文件路径"

3. 运行脚本:
   python main.py

工作流程:
1. 读取输入文件，生成字幕(SRT)和时间轴(JSON)
2. 上传输入文件获取file_id
3. 提交语音合成任务
4. 轮询任务状态直到完成
5. 下载合成结果

输出文件:
- output.mp3: 合成的语音文件
- output.srt: SRT格式字幕文件
- output_timeline.json: JSON格式时间轴文件
"""

import requests
import json
import os
import time
import sys
import re
from pathlib import Path


class MinimaxTTS:
    def __init__(self):
        # 读取配置（环境变量优先级高于配置文件）
        self.config = self._load_config()
        self.api_key = self.config.get('MINIMAX_API_KEY')

        if not self.api_key:
            print("错误: 未找到 MINIMAX_API_KEY")
            print("请通过以下方式之一设置API密钥:")
            print("1. 环境变量: export MINIMAX_API_KEY='your_key'")
            print("2. 配置文件: 在 config.env 或 .env 文件中设置 MINIMAX_API_KEY=your_key")
            sys.exit(1)

        self.base_url = "https://api.minimaxi.com/v1"

    def _load_config(self):
        """从环境变量和配置文件加载配置"""
        config = {}

        # 首先从配置文件读取
        config_files = [Path(__file__).parent / ".env", Path(__file__).parent / "config.env"]
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    if value:  # 只保存非空值
                                        config[key] = value
                except Exception as e:
                    print(f"读取配置文件 {config_file} 失败: {e}")

        # 环境变量覆盖配置文件（环境变量优先级更高）
        for key in ['MINIMAX_API_KEY', 'INPUT_FILE_PATH', 'OUTPUT_FILENAME']:
            env_value = os.environ.get(key)
            if env_value:
                config[key] = env_value

        return config

    def upload_file(self, file_path):
        """上传文件获取file_id"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"输入文件不存在: {file_path}")

        # 根据文件扩展名确定MIME类型
        file_extension = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.zip': 'application/zip',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json'
        }
        mime_type = mime_types.get(file_extension, 'application/octet-stream')

        url = f"{self.base_url}/files/upload"
        payload = {'purpose': 't2a_async_input'}
        files = [
            ('file', (os.path.basename(file_path), open(file_path, 'rb'), mime_type))
        ]
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        print(f"正在上传文件: {file_path}")
        response = requests.post(url, headers=headers, data=payload, files=files)
        response.raise_for_status()

        result = response.json()
        print(f"文件上传响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # 检查API响应状态
        base_resp = result.get('base_resp', {})
        if base_resp.get('status_code') != 0:
            raise ValueError(f"文件上传失败: {base_resp.get('status_msg', '未知错误')}")

        # 获取file_id（支持多种API响应格式）
        file_id = (result.get('file_id') or
                  result.get('data', {}).get('file', {}).get('id') or
                  result.get('file', {}).get('file_id'))
        if not file_id:
            raise ValueError(f"上传失败，无法获取文件ID。完整响应: {result}")

        print(f"文件上传成功，file_id: {file_id}")
        return file_id

    def submit_tts_task(self, file_id=None):
        """提交语音合成任务"""
        if not file_id:
            raise ValueError("必须提供文件ID")

        url = f"{self.base_url}/t2a_async_v2"
        payload = {
            "model": "speech-02-hd",
            "language_boost": "auto",
            "voice_setting": {
                "voice_id": "female-shaonv",
                "speed": 1,
                "vol": 1,
                "pitch": 1
            },
            "audio_setting": {
                "audio_sample_rate": 44100,
                "bitrate": 256000,
                "format": "mp3",
                "channel": 2
            },
            "voice_modify": {
                "pitch": 0,
                "intensity": 0,
                "timbre": 0
            }
        }

        payload["text_file_id"] = file_id

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        print("正在提交语音合成任务...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"API响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # 检查API响应状态
        base_resp = result.get('base_resp', {})
        if base_resp.get('status_code') != 0:
            raise ValueError(f"API错误: {base_resp.get('status_msg', '未知错误')}")

        # 直接从根级别获取task_id
        task_id = result.get('task_id')
        if not task_id:
            raise ValueError(f"任务提交失败，无法获取任务ID。完整响应: {result}")

        print(f"任务提交成功，task_id: {task_id}")
        return task_id

    def query_task_status(self, task_id):
        """查询任务状态"""
        url = f"{self.base_url}/query/t2a_async_query_v2"
        params = {'task_id': task_id}
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'content-type': 'application/json'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()
        print(f"状态查询响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result

    def wait_for_completion(self, task_id, max_attempts=60, delay=5):
        """等待任务完成"""
        print("正在等待任务完成...")
        for attempt in range(max_attempts):
            try:
                result = self.query_task_status(task_id)

                # 检查API响应状态
                base_resp = result.get('base_resp', {})
                if base_resp.get('status_code') != 0:
                    raise RuntimeError(f"API查询失败: {base_resp.get('status_msg', '未知错误')}")

                # 直接从根级别获取状态
                status = result.get('status')

                if status == 'Success':
                    # 直接从根级别获取文件ID
                    file_id = result.get('file_id')
                    print("任务完成！")
                    return file_id
                elif status == 'Processing':
                    print(f"任务进行中... ({attempt + 1}/{max_attempts})")
                elif status in ['Failed', 'Cancel']:
                    raise RuntimeError(f"任务失败: {status}")
                else:
                    print(f"未知状态: {status}")

            except Exception as e:
                print(f"查询状态时出错: {e}")

            if attempt < max_attempts - 1:
                time.sleep(delay)

        raise TimeoutError("任务超时")

    def download_file(self, file_id, output_filename="output.mp3"):
        """下载合成结果"""
        url = f"{self.base_url}/files/retrieve_content"
        params = {'file_id': file_id}
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        print(f"正在下载文件: {output_filename}")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        with open(output_filename, 'wb') as f:
            f.write(response.content)

        print(f"文件下载完成: {output_filename}")
        return output_filename


class SubtitleGenerator:
    """字幕生成器 - 根据文本和语速生成SRT字幕文件"""

    def __init__(self, chars_per_second=4.5):
        """
        初始化字幕生成器

        Args:
            chars_per_second: 每秒朗读的字符数（中文），默认4.5字/秒
                             - 正常语速: 4-5 字/秒
                             - 较快语速: 5-6 字/秒
                             - 较慢语速: 3-4 字/秒
        """
        self.chars_per_second = chars_per_second

    def split_text_into_sentences(self, text):
        """
        将文本分割成句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        # 按中文标点符号分割（句号、问号、感叹号、分号）
        # 保留标点符号在句子末尾
        sentences = re.split(r'(?<=[。！？；\n])', text)
        # 清理空白句子
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def estimate_duration(self, text):
        """
        估算文本朗读时长

        Args:
            text: 文本内容

        Returns:
            估算的秒数
        """
        # 计算有效字符数（去除标点和空格）
        effective_chars = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        char_count = len(effective_chars)

        # 根据语速计算时长，最少0.5秒
        duration = max(char_count / self.chars_per_second, 0.5)
        return duration

    def generate_timeline(self, sentences):
        """
        为句子列表生成时间轴

        Args:
            sentences: 句子列表

        Returns:
            包含(开始时间, 结束时间, 文本)的列表
        """
        timeline = []
        current_time = 0.0

        for sentence in sentences:
            duration = self.estimate_duration(sentence)
            start_time = current_time
            end_time = current_time + duration
            timeline.append({
                'start': start_time,
                'end': end_time,
                'text': sentence
            })
            current_time = end_time

        return timeline

    def format_srt_time(self, seconds):
        """
        将秒数转换为SRT时间格式

        Args:
            seconds: 秒数

        Returns:
            SRT格式时间字符串 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt(self, timeline, output_file):
        """
        生成SRT字幕文件

        Args:
            timeline: 时间轴列表
            output_file: 输出文件路径

        Returns:
            输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, item in enumerate(timeline, 1):
                start_str = self.format_srt_time(item['start'])
                end_str = self.format_srt_time(item['end'])
                text = item['text']

                f.write(f"{i}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")

        print(f"字幕文件生成完成: {output_file}")
        return output_file

    def generate_json_timeline(self, timeline, output_file):
        """
        生成JSON格式的时间轴文件

        Args:
            timeline: 时间轴列表
            output_file: 输出文件路径

        Returns:
            输出文件路径
        """
        # 添加序号
        for i, item in enumerate(timeline, 1):
            item['index'] = i

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)

        print(f"时间轴JSON文件生成完成: {output_file}")
        return output_file

    def process_file(self, input_file, srt_output=None, json_output=None):
        """
        处理输入文件，生成字幕和时间轴

        Args:
            input_file: 输入文本文件路径
            srt_output: SRT输出文件路径（可选）
            json_output: JSON输出文件路径（可选）

        Returns:
            (timeline, srt_path, json_path) 元组
        """
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()

        # 分割句子
        sentences = self.split_text_into_sentences(text)
        print(f"📝 文本分割为 {len(sentences)} 个句子")

        # 生成时间轴
        timeline = self.generate_timeline(sentences)

        # 计算总时长
        if timeline:
            total_duration = timeline[-1]['end']
            print(f"⏱️ 预估总时长: {self.format_srt_time(total_duration)}")

        # 生成输出文件名
        base_name = os.path.splitext(input_file)[0]
        srt_path = srt_output or f"{base_name}.srt"
        json_path = json_output or f"{base_name}_timeline.json"

        # 生成SRT文件
        self.generate_srt(timeline, srt_path)

        # 生成JSON时间轴
        self.generate_json_timeline(timeline, json_path)

        return timeline, srt_path, json_path


def main():
    """主工作流"""
    # 调试信息
    print("=== Minimax 语音合成工具 ===")

    tts = MinimaxTTS()

    # 显示配置信息
    config = tts.config
    print(f"✅ API密钥: {config['MINIMAX_API_KEY'][:10]}...")

    # 获取输入文件路径
    input_file_path = config.get("INPUT_FILE_PATH")

    print(f"📁 INPUT_FILE_PATH: {input_file_path or '未设置'}")

    if not input_file_path:
        print("❌ 错误: 请设置 INPUT_FILE_PATH")
        print("可以在配置文件中设置，或使用环境变量")
        print("INPUT_FILE_PATH: 文件路径（支持 .txt, .md, .json, .zip）")
        sys.exit(1)

    try:
        # 生成字幕和时间轴
        print("\n📋 生成字幕和时间轴...")
        subtitle_gen = SubtitleGenerator(chars_per_second=4.5)  # 可调整语速
        base_name = os.path.splitext(input_file_path)[0]
        output_file = config.get("OUTPUT_FILENAME", "output.mp3")
        output_base = os.path.splitext(output_file)[0]

        # 生成字幕文件
        timeline, srt_path, json_path = subtitle_gen.process_file(
            input_file_path,
            srt_output=f"{output_base}.srt",
            json_output=f"{output_base}_timeline.json"
        )

        # 上传文件获取file_id
        file_id = tts.upload_file(input_file_path)

        # 提交合成任务
        task_id = tts.submit_tts_task(file_id=file_id)

        # 等待完成
        result_file_id = tts.wait_for_completion(task_id)

        # 下载结果
        tts.download_file(result_file_id, output_file)

        print("\n✅ 语音合成完成！")
        print(f"🎵 音频文件: {output_file}")
        print(f"📝 字幕文件: {srt_path}")
        print(f"📊 时间轴文件: {json_path}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
