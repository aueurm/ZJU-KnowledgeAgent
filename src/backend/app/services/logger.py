"""
统一日志模块
职责：为整个后端提供统一的日志配置和命名 logger 获取接口
"""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    配置全局日志格式和输出
    格式：[时间] [级别] [模块] 消息
    """
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 避免重复添加 handler
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取命名 logger
    用法：from app.services.logger import get_logger
          logger = get_logger(__name__)
    """
    return logging.getLogger(name)
