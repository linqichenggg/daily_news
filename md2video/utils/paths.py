"""Path utilities for md2video package."""
from pathlib import Path
from datetime import date, datetime
import os


def get_project_root() -> Path:
    """获取 md2video 项目根目录（基于此文件位置）
    
    Returns:
        md2video 目录的绝对路径
    """
    return Path(__file__).parent.parent.resolve()


def get_logs_dir() -> Path:
    """获取日志目录路径
    
    Returns:
        logs 目录的绝对路径
    """
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_log_file_path(prefix: str = "main") -> str:
    """获取日志文件路径
    
    Args:
        prefix: 日志文件前缀 (如 'main', 'md2html', 'md2audio' 等)
    
    Returns:
        日志文件的完整路径字符串
    """
    logs_dir = get_logs_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return str(logs_dir / f"{timestamp}_{prefix}.log")


def get_output_dir(subdir: str = "") -> Path:
    """Get standardized output directory path.
    
    Args:
        subdir: Subdirectory name (e.g. 'images', 'videos')
    
    Returns:
        Path object to output directory
    """
    today = date.today().strftime("%Y%m%d")
    output_path = get_project_root() / "output" / today / subdir
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def get_output_base_dir() -> Path:
    """获取 output 基础目录路径
    
    Returns:
        output 目录的绝对路径
    """
    output_dir = get_project_root() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_relative_path(file_path: str) -> Path:
    """Convert file path to be relative to package root.
    
    Args:
        file_path: Input file path
        
    Returns:
        Relative Path object
    """
    return Path(os.path.relpath(file_path, start=get_project_root()))
