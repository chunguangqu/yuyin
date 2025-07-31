import asyncio
import logging
import os
import subprocess
import time
import uuid
import wave
from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
import pyaudio
from pydub import AudioSegment
from gtts import gTTS
import edge_tts
import ChatTTS
import torch
import torchaudio
import soundfile as sf

logger = logging.getLogger(__name__)


class AbstractTTS(ABC):
    __metaclass__ = ABCMeta

    @abstractmethod
    def to_tts(self, text):
        pass

    def synthesize(self, text, lang='zh'):
        """所有子类都应实现此方法以支持多语种"""
        pass

class GTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file")
        self.lang = config.get("lang")

    def _generate_filename(self, extension=".aiff"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"执行时间: {execution_time:.2f} 秒")

    def to_tts(self, text, lang='zh'):
        return self.synthesize(text, lang)

    def synthesize(self, text, lang='zh'):
        # gTTS支持多语种，lang参数直接传递
        tmpfile = self._generate_filename(".aiff")
        try:
            start_time = time.time()
            tts = gTTS(text=text, lang=lang)
            tts.save(tmpfile)
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.debug(f"生成TTS文件失败: {e}")
            return None

class EdgeTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file", "tmp/")
        self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.en_voice = config.get("en_voice", "en-US-AriaNeural")

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    async def text_to_speak(self, text, output_file, voice):
        communicate = edge_tts.Communicate(text, voice=voice)
        await communicate.save(output_file)

    def to_tts(self, text, lang='zh'):
        return self.synthesize(text, lang)

    def synthesize(self, text, lang='zh'):
        # 根据lang选择voice
        if lang == 'en':
            voice = self.en_voice
        else:
            voice = self.voice
            
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        
        try:
            # 尝试获取当前正在运行的事件循环
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果没有正在运行的事件循环，则创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 确保在正确的事件循环中运行异步任务
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.text_to_speak(text, tmpfile, voice), loop)
            future.result()  # 同步等待结果
        else:
            loop.run_until_complete(self.text_to_speak(text, tmpfile, voice))
            
        self._log_execution_time(start_time)
        return tmpfile

def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")
