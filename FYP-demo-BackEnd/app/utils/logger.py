import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import multiprocessing


# Global flag to avoid duplicate initialization
_logger_initialized = False
_log_file_path = None


def setup_file_logging(
    log_path: Optional[str] = None, log_level: str = "INFO"
) -> logging.Logger:
    """
    Setup file logging recorder

    Args:
        log_path: Log file save path, defaults to LOG_PATH environment variable
        log_level: Log level, defaults to LOG_LEVEL environment variable

    Returns:
        Configured logger instance
    """
    global _logger_initialized, _log_file_path

    # 如果已经初始化，直接返回根日志记录器
    if _logger_initialized:
        return logging.getLogger()

    # 从环境变量获取配置
    if log_path is None:
        log_path = os.getenv("LOG_PATH", "logs/")

    log_level = os.getenv("LOG_LEVEL", log_level).upper()

    # 确保日志目录存在
    log_dir = Path(log_path)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否是主进程，如果不是且已有日志文件，使用已有的
    is_main_process = multiprocessing.current_process().name == "MainProcess"

    if not is_main_process and _log_file_path is None:
        # 查找最新的日志文件
        existing_logs = list(log_dir.glob("*.log"))
        if existing_logs:
            _log_file_path = max(existing_logs, key=lambda x: x.stat().st_mtime)
        else:
            # 如果没有现有日志文件，创建一个新的
            now = datetime.now()
            log_filename = now.strftime("%y-%m-%d_%H-%M-%S.log")
            _log_file_path = log_dir / log_filename
    elif _log_file_path is None:
        # 主进程或首次初始化，创建新日志文件
        now = datetime.now()
        log_filename = now.strftime("%y-%m-%d_%H-%M-%S.log")
        _log_file_path = log_dir / log_filename

    # 获取根日志记录器
    logger = logging.getLogger()

    # 清除现有的处理器，避免重复
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 设置日志级别
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 创建文件处理器
    file_handler = logging.FileHandler(_log_file_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    file_handler.setFormatter(formatter)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 标记为已初始化
    _logger_initialized = True

    # 记录日志文件位置（只在主进程记录）
    if is_main_process:
        logger.info(f"Log file created: {_log_file_path}")
        logger.info(f"Log level set to: {log_level}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


def cleanup_old_logs(log_path: Optional[str] = None, keep_days: int = 30):
    """
    清理旧的日志文件

    Args:
        log_path: 日志文件保存路径
        keep_days: 保留天数，默认30天
    """
    if log_path is None:
        log_path = os.getenv("LOG_PATH", "logs/")

    log_dir = Path(log_path)
    if not log_dir.exists():
        return

    current_time = datetime.now()

    for log_file in log_dir.glob("*.log"):
        try:
            # 获取文件创建时间
            file_time = datetime.fromtimestamp(log_file.stat().st_ctime)

            # 如果文件超过保留天数，删除它
            if (current_time - file_time).days > keep_days:
                log_file.unlink()
                print(f"Deleted expired log file: {log_file}")
        except Exception as e:
            print(f"Error cleaning log file {log_file}: {e}")
