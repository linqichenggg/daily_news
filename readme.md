单机游戏日报视频版技术概述：

数据来源是 Reddit 和 3DM 抓取， Gemini-2.5-flash 整理

TTS 使用的是 MiniMax 的 speech-02-hd 模型的 female-shaonv 音色，合成语音的同时，通过代码同步输出时间轴和字幕。

内容使用 DeepSeek-V3 生成网页，python 启动无头浏览器截图

视频由 MoviePy 合成。

目录下:
news2md 与 md2video 分别代表 数据收集 和 视频制作 部分。
minimax 与 gemini_test 为功能模块化部分，删去不影响执行