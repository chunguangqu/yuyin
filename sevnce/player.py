import logging
import queue
import threading
from pydub import  AudioSegment
import pygame
import os
logger = logging.getLogger(__name__)

class AbstractPlayer(object):
    def __init__(self, *args, recording_event=None, **kwargs):
        super(AbstractPlayer, self).__init__()
        self.is_playing = False
        self.play_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.consumer_thread = threading.Thread(target=self._playing)
        self.consumer_thread.start()
        self.recording_event = recording_event

    @staticmethod
    def to_wav(audio_file):
        tmp_file = audio_file# + ".wav"
        wav_file = AudioSegment.from_file(audio_file)
        wav_file.export(tmp_file, format="wav")
        return tmp_file

    def _playing(self):
        while not self._stop_event.is_set():
            data = self.play_queue.get()
            self.is_playing = True
            try:
                if self.recording_event is not None:
                    self.recording_event.clear()  # 播放前暂停采集
                self.do_playing(data)
            except Exception as e:
                logger.error(f"播放音频失败: {e}")
            finally:
                if self.recording_event is not None:
                    self.recording_event.set()  # 播放后恢复采集
                self.play_queue.task_done()
                self.is_playing = False

    def play(self, data):
        logger.info(f"play file {data}")
        audio_file = self.to_wav(data)
        self.play_queue.put(audio_file)

    def stop(self):
        self._clear_queue()

    def shutdown(self):
        self._clear_queue()
        self._stop_event.set()
        if self.consumer_thread.is_alive():
            self.consumer_thread.join()

    def get_playing_status(self):
        """正在播放和队列非空，为正在播放状态"""
        return self.is_playing or (not self.play_queue.empty())

    def _clear_queue(self):
        with self.play_queue.mutex:
            self.play_queue.queue.clear()

    def do_playing(self, audio_file):
        """播放音频的具体实现，由子类实现"""
        raise NotImplementedError("Subclasses must implement do_playing")

    def wait_for_completion(self):
        """阻塞直到播放队列全部播放完毕"""
        while self.get_playing_status():
            import time
            time.sleep(0.1)

class PygameSoundPlayer(AbstractPlayer):
    """支持预加载"""
    def __init__(self, *args, **kwargs):
        super(PygameSoundPlayer, self).__init__(*args, **kwargs)
        # 改进pygame音频初始化，增加缓冲区大小
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=8192)
        # 设置音频缓冲区大小
        pygame.mixer.set_reserved(1)  # 保留一个声道

    def do_playing(self, current_sound):
        try:
            logger.debug("PygameSoundPlayer 播放音频中")
            # 获取保留的声道
            channel = pygame.mixer.Channel(0)

            # 设置音量避免过载
            channel.set_volume(0.8)
            # 播放音频
            channel.play(current_sound)

            # 等待播放完成，增加更频繁的检查
            while channel.get_busy():
                pygame.time.Clock().tick(60)  # 降低检查频率，减少CPU占用
                # 添加短暂休眠，让出CPU时间
                pygame.time.wait(10)

            # 清理资源
            channel.stop()
            del current_sound
            logger.debug(f"PygameSoundPlayer 播放完成")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            # 确保清理资源
            try:
                pygame.mixer.Channel(0).stop()
            except:
                pass

    def play(self, data):
        logger.info(f"play file {data}")
        audio_file = data
        try:
            # 添加音频文件验证
            if not os.path.exists(audio_file):
                logger.error(f"音频文件不存在: {audio_file}")
                return

            sound = pygame.mixer.Sound(audio_file)
            self.play_queue.put(sound)
        except Exception as e:
            logger.error(f"加载音频文件失败: {e}")

    def stop(self):
        super().stop()
        # 停止所有音频播放
        try:
            pygame.mixer.stop()
        except:
            pass

    def shutdown(self):
        super().shutdown()
        # 清理pygame资源
        try:
            pygame.mixer.quit()
        except:
            pass

def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")