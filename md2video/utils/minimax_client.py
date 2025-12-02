import requests
import json
import os
import time
import re
from pathlib import Path

class MinimaxTTS:
    def __init__(self, api_key, base_url="https://api.minimaxi.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY is required")

    def upload_file(self, file_path):
        """上传文件获取file_id"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

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

        print(f"Uploading file: {file_path}")
        response = requests.post(url, headers=headers, data=payload, files=files)
        response.raise_for_status()

        result = response.json()
        
        # Check API status
        base_resp = result.get('base_resp', {})
        if base_resp.get('status_code') != 0:
            raise ValueError(f"File upload failed: {base_resp.get('status_msg', 'Unknown error')}")

        # Get file_id
        file_id = (result.get('file_id') or
                  result.get('data', {}).get('file', {}).get('id') or
                  result.get('file', {}).get('file_id'))
        if not file_id:
            raise ValueError(f"Upload failed, no file_id. Response: {result}")

        print(f"File uploaded successfully, file_id: {file_id}")
        return file_id

    def submit_tts_task(self, file_id):
        """提交语音合成任务"""
        if not file_id:
            raise ValueError("file_id is required")

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

        print("Submitting TTS task...")
        
        # 增加重试逻辑
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Task submission failed ({attempt+1}/{max_retries}), retrying... Error: {e}")
                    time.sleep(2)
                else:
                    raise e

        result = response.json()

        # Check API status
        base_resp = result.get('base_resp', {})
        if base_resp.get('status_code') != 0:
            raise ValueError(f"API Error: {base_resp.get('status_msg', 'Unknown error')}")

        # Get task_id
        task_id = result.get('task_id')
        if not task_id:
            raise ValueError(f"Task submission failed, no task_id. Response: {result}")

        print(f"Task submitted, task_id: {task_id}")
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
        return response.json()

    def wait_for_completion(self, task_id, max_attempts=120, delay=2):
        """等待任务完成"""
        print("Waiting for task completion...")
        for attempt in range(max_attempts):
            try:
                result = self.query_task_status(task_id)
                
                base_resp = result.get('base_resp', {})
                if base_resp.get('status_code') != 0:
                    raise RuntimeError(f"API Query Failed: {base_resp.get('status_msg', 'Unknown error')}")

                status = result.get('status')

                if status == 'Success':
                    file_id = result.get('file_id')
                    print("Task Completed!")
                    return file_id
                elif status == 'Processing':
                    # print(f"Processing... ({attempt + 1}/{max_attempts})")
                    pass
                elif status in ['Failed', 'Cancel']:
                    raise RuntimeError(f"Task Failed: {status}")
                
            except Exception as e:
                print(f"Error querying status: {e}")

            if attempt < max_attempts - 1:
                time.sleep(delay)

        raise TimeoutError("Task Timeout")

    def download_file(self, file_id, output_filename):
        """下载合成结果"""
        url = f"{self.base_url}/files/retrieve_content"
        params = {'file_id': file_id}
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        print(f"Downloading file to: {output_filename}")
        
        # 增加重试逻辑
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=60)
                response.raise_for_status()
                
                # 验证内容长度是否有效（简单判断）
                if len(response.content) < 100: # 如果文件太小可能是错误信息
                    print(f"Warning: Downloaded file size is very small ({len(response.content)} bytes)")
                
                break
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Download failed ({attempt+1}/{max_retries}), retrying... Error: {e}")
                    time.sleep(2)
                else:
                    raise e

        with open(output_filename, 'wb') as f:
            f.write(response.content)

        return output_filename

class SubtitleGenerator:
    """字幕生成器 - 根据文本和语速生成SRT字幕文件"""

    def __init__(self, chars_per_second=4.5):
        self.chars_per_second = chars_per_second

    def split_text_into_sentences(self, text, max_length=30):
        """
        智能拆分文本为字幕片段，确保单行显示
        Args:
            text: 输入文本
            max_length: 单行字幕最大字符数（默认22，适合1920宽度视频）
        """
        # 第一步：按主要标点符号切分
        sentences = re.split(r'(?<=[，。！？；：,!.?;:])', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 第二步：对过长的句子进行二次拆分
        final_sentences = []
        for sentence in sentences:
            if len(sentence) <= max_length:
                final_sentences.append(sentence)
            else:
                # 句子过长，需要智能拆分
                parts = self._split_long_sentence(sentence, max_length)
                final_sentences.extend(parts)
        
        return final_sentences
    
    def _split_long_sentence(self, sentence, max_length):
        """
        将过长的句子拆分成多个短句
        优先在逗号、顿号等位置拆分，保持语义完整
        """
        if len(sentence) <= max_length:
            return [sentence]
        
        parts = []
        current = ""
        
        # 优先拆分点：逗号、顿号、冒号、分号
        split_chars = ['，', '、', '：', '；', ',', ';']
        
        i = 0
        while i < len(sentence):
            current += sentence[i]
            
            # 如果当前片段达到合理长度且遇到拆分点
            if len(current) >= max_length * 0.6 and sentence[i] in split_chars:
                parts.append(current.strip())
                current = ""
            # 如果当前片段超过最大长度，强制拆分
            elif len(current) >= max_length:
                # 尝试回退到最近的空格或标点
                split_pos = max_length
                for j in range(len(current) - 1, max(0, len(current) - 5), -1):
                    if current[j] in split_chars + [' ', '　']:
                        split_pos = j + 1
                        break
                
                parts.append(current[:split_pos].strip())
                current = current[split_pos:].strip()
            
            i += 1
        
        # 添加剩余部分
        if current.strip():
            parts.append(current.strip())
        
        return parts

    def estimate_duration(self, text):
        # 计算有效字符数（去除标点和空格）
        effective_chars = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        char_count = len(effective_chars)
        # 根据语速计算时长，最少0.5秒
        duration = max(char_count / self.chars_per_second, 0.5)
        return duration

    def generate_timeline(self, sentences, start_offset=0.0):
        """
        为句子列表生成时间轴
        Args:
            sentences: 句子列表
            start_offset: 起始时间偏移量(秒)
        """
        timeline = []
        current_time = start_offset

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
