import logging
from logging.handlers import TimedRotatingFileHandler

def set_logger(level=logging.INFO):
    # filename:"/root/run.log"（保存的文件目录）
    # when:"D"(时间计量单位)
        # S - Seconds
        # M - Minutes
        # H - Hours
        # D - Days
        # midnight - roll over at midnight
        # W{0-6} - roll over on a certain day; 0 - Monday
    #interval:30(保留30D数据 即30天的数据)
    #backupCount（仅保留一份数据 即一月数据，若等于2则保留两月数据 ）
    #utc:False（不使用UTC时间）
    #encoding:utf-8（使用utf-8编码）
    logHandler = TimedRotatingFileHandler("./run.log", when="D",interval=30,backupCount=1,utc=False,encoding="utf-8")
    #日志中时间显示格式 年-月-天 时：分：秒
    logFormatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s','%Y-%m-%d %H:%M:%S')
    logHandler.setFormatter(logFormatter)
    logger = logging.getLogger(__name__)
    logger.addHandler(logHandler)
    #设置日志显示等级
    logger.setLevel(level)
    return logger

# 默认使用INFO级别
logger = set_logger()

def update_log_level(level_name):
    """更新日志级别"""
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = level_map.get(level_name.lower(), logging.INFO)
    logger.setLevel(level)
    # 同时更新所有子模块的日志级别
    logging.getLogger('sevnce').setLevel(level)
    logging.getLogger('sevnce.recorder').setLevel(level)
    logging.getLogger('sevnce.vad').setLevel(level)
    logging.getLogger('sevnce.robot').setLevel(level)
    logging.getLogger('sevnce.audio_processor').setLevel(level)