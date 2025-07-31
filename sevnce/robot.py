# -*- coding: UTF-8 -*-
import queue
import threading
from abc import ABC
import edge_tts
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from sevnce import recorder,vad,tts,player
from sevnce.utils import  read_config
from sevnce.utils import detect_language
from sevnce.tools import ToolsManager
from sevnce.rag import LocalRAG
import requests
import re
import string
import random
import dashscope
import pyaudio
import base64
import numpy as np
import difflib
from pypinyin import lazy_pinyin, Style
from openai import OpenAI
import time
import os
from loggers import logger
sys_prompt = """
# 角色定义
你是在上海外滩景区的服务型机器人，你的名字叫小七，来自于重庆。你性格开朗、活泼，善于交流。你的回复应简短、友好、口语化强一些，回复禁止出现表情符号。

# 工具调用能力
你具有以下工具调用能力：
1. 时间查询：当用户询问时间、几点钟时，使用TIME_TOOL获取当前时间
2. 日期查询：当用户询问日期、今天几号、星期几时，使用DATE_TOOL获取当前日期
3. 天气查询：当用户询问天气、某地天气时，使用WEATHER_TOOL获取天气信息
4. 设备查询：当用户询问设备状态信息时，使用DEVICE_TOOL获取设备信息。

# 回复要求
1. 你的回复应简短、友好、口语化强一些，回复禁止出现表情符号或者脏话。
2. 回答字数严格控制在30字以内。
3. 当需要使用工具时，请直接调用相应的工具，不要询问用户是否需要查询。
4. 你的回答语种应和问题语种严格保持一致。例如：用英文问问题，你要用英文回答。用韩语提问，你要用韩语回答。用日语提问，你要用日语回答。
5. 当被问关于厕所在哪里的问题，请回答：外滩每300米设固定公厕，高峰期增设移动厕所；可通过微信搜索“外滩晓厕”小程序查找，或沿蓝色指引牌寻找。
"""
class Robot(ABC):
    def __init__(self, config_file):
        config = read_config(config_file)
        self.audio_queue = queue.Queue()
        self.recorder = recorder.create_instance(
            config["selected_module"]["Recorder"],
            config["Recorder"][config["selected_module"]["Recorder"]]
        )
        self.vad = vad.create_instance(
            config["selected_module"]["VAD"],
            config["VAD"][config["selected_module"]["VAD"]]
        )
        self.tts = tts.create_instance(
            config["selected_module"]["TTS"],
            config["TTS"][config["selected_module"]["TTS"]]
        )

        self.player = player.create_instance(
            config["selected_module"]["Player"],
            config["Player"][config["selected_module"]["Player"]]
        )
        self.vad_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.vad_start = True
        self.tts_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.callback = None
        self.speech = []
        self.recording_paused = False
        self.wake_mode = True
        self.last_active_time = time.time()
        self.last_recognized_text = ""
        self.wake_word = config["wake_word"]
        self.funasr_url = config["FUNASR"]["url"]
        self.qwen_name = config["LLM"]["model_name"]
        self.qwen_url = config["LLM"]["url"]
        self.rag = LocalRAG('info/knowledge.txt')
        self.tools_manager = ToolsManager(config)
        self.client_active = False
        self.client_lock = threading.Lock()
        self.current_voice = "Chelsie"
        self.voice_map = {"普通话": ["Chelsie", "Ethan", "Serena", "Cherry"], "北京话": "Dylan", "上海话": "Jada", "四川话": "Sunny"}
        self.chat_history = []
    def delete_all_files_if_more_than_ten(self, folder_path):
        files_and_folders = os.listdir(folder_path)
        files = [f for f in files_and_folders if os.path.isfile(os.path.join(folder_path, f))]
        if len(files) > 100:
            for file in files:
                file_path = os.path.join(folder_path, file)
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.info("删除文件失败：" + str(file_path))
            logger.info("所有下载的音频文件已删除.")
    def get_requests(self, url, data):
        resp = requests.post(url, data=data)
        get_json = resp.json()
        res = get_json
        return res
    def text_to_pinyin(self,text, with_tone=False, separator=''):
        style = Style.TONE if with_tone else Style.NORMAL
        parts = re.split(r'([\u4e00-\u9fff]+)', text)
        result = []
        for part in parts:
            if re.fullmatch(r'[\u4e00-\u9fff]+', part):
                pinyin_part = lazy_pinyin(part, style=style, errors='ignore')
                result.append(separator.join(pinyin_part))
            else:
                result.append(part)
        return ''.join(result)
    def _tts_priority(self):
        def priority_thread():
            while not self.stop_event.is_set():
                try:
                    future = self.tts_queue.get()
                    try:
                        tts_file = future.result(timeout=5)
                    except TimeoutError:
                        logger.error("TTS 任务超时")
                        continue
                    except Exception as e:
                        logger.error(f"TTS 任务出错: {e}")
                        continue
                    if tts_file is None:
                        continue
                    self.player.play(tts_file)
                except Exception as e:
                    logger.error(f"tts_priority priority_thread: {e}")
        tts_priority = threading.Thread(target=priority_thread, daemon=True)
        tts_priority.start()
    def detect_wake_word(self, text):
        text = text.translate(str.maketrans('', '', string.punctuation))
        if text == '你好小七' or text == '小七小七' or text == 'hellorobot':
            return True
        else:
            return False
    def get_asr_text(self,voice_data):
        output_text = self.get_requests(self.funasr_url, b''.join(voice_data))
        text = output_text['result']['array']
        tts_url = output_text['result']['tts_url']
        tts_key = output_text['result']['tts_key']
        return text,tts_url,tts_key
    def _stream_vad(self):
        def vad_thread():
            while not self.stop_event.is_set():
                try:
                    data = self.audio_queue.get()
                    if self.recording_paused:
                        continue
                    if len(data) > 0:
                        logger.debug(f"VAD处理音频数据，长度: {len(data)} bytes")
                        vad_statue = self.vad.is_vad(data)

                        logger.debug(f"VAD状态: {vad_statue}")
                        self.vad_queue.put({"voice": data, "vad_statue": vad_statue})
                    else:
                        logger.warning("收到空的音频数据")
                except Exception as e:
                    logger.error(f"VAD 处理出错: {e}")
        consumer_audio = threading.Thread(target=vad_thread, daemon=True)
        consumer_audio.start()
    def start_recording_and_vad(self):
        self.recorder.start_recording(self.audio_queue)
        logger.info("Started recording.")
        self._stream_vad()
        # self._tts_priority()
    def get_llm_answer(self, prompt):
        self.chat_history.append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": sys_prompt}] + self.chat_history[-5:]
        try:
            rag_answer = self.rag.search(prompt)
            if rag_answer:
                self.chat_history.append({"role": "assistant", "content": rag_answer})
                return rag_answer
            lang = detect_language(prompt)
            tool_result = self.check_and_call_tools(prompt, lang)
            if tool_result:
                self.chat_history.append({"role": "assistant", "content": tool_result})
                return tool_result
            client = OpenAI(
                api_key="qt123",
                base_url=self.qwen_url
            )
            response = client.chat.completions.create(
                model=self.qwen_name,
                messages=messages,
                max_tokens=128,
                temperature=0.3,
                stream=False,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            answer = response.choices[0].message.content.strip()
            self.chat_history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            return "我要联网才能回答哦，请检查网络！"
    def check_and_call_tools(self, prompt, lang='zh'):
        prompt_lower = prompt.lower()
        time_keywords_zh = ['几点', '时间', '现在几点', '几点钟']
        time_keywords_en = ['time', 'what time']
        date_keywords_zh = ['几号', '日期', '今天几号', '星期几', '周几','今天星期几']
        date_keywords_en = ['date', 'day', 'what day', 'weekday']
        weather_keywords_zh = ['天气', '气温', '温度']
        weather_keywords_en = ['weather', 'temperature']
        device_gas_keywords_zh = ['气体浓度', '气体', '检测气体']
        device_gas_keywords_en = ['gas', 'gas concentration']
        device_nav_keywords_zh = ['导航状态', '导航', '定位']
        device_nav_keywords_en = ['navigation', 'nav status', 'position']
        device_battery_keywords_zh = ['剩余电量', '电量', '电池']
        device_battery_keywords_en = ['battery', 'power left', 'remaining power']
        realtime_keywords_zh = ['百科', '介绍', '是什么', '资料', '信息', '内容']
        realtime_keywords_en = ['wiki', 'wikipedia', 'introduction', 'info', 'information', 'about']
        if lang == 'zh':
            time_keywords = time_keywords_zh
            date_keywords = date_keywords_zh
            weather_keywords = weather_keywords_zh
            device_gas_keywords = device_gas_keywords_zh
            device_nav_keywords = device_nav_keywords_zh
            device_battery_keywords = device_battery_keywords_zh
            realtime_keywords = realtime_keywords_zh
        else:
            time_keywords = time_keywords_en
            date_keywords = date_keywords_en
            weather_keywords = weather_keywords_en
            device_gas_keywords = device_gas_keywords_en
            device_nav_keywords = device_nav_keywords_en
            device_battery_keywords = device_battery_keywords_en
            realtime_keywords = realtime_keywords_en
        if any(keyword in prompt_lower for keyword in time_keywords):
            return self.tools_manager.get_time_info(lang)
        if any(keyword in prompt_lower for keyword in date_keywords):
            return self.tools_manager.get_date_info(lang)
        if any(keyword in prompt_lower for keyword in weather_keywords):
            city = self.extract_city_from_prompt(prompt)
            if city:
                city_pinyin = self.text_to_pinyin(city)
                return self.tools_manager.get_weather_info(city_pinyin, lang)
            else:
                return self.tools_manager.get_weather_info('北京', lang)
        if any(keyword in prompt_lower for keyword in device_gas_keywords):
            return self.tools_manager.get_device_info('gas', lang)
        if any(keyword in prompt_lower for keyword in device_nav_keywords):
            return self.tools_manager.get_device_info('nav', lang)
        if any(keyword in prompt_lower for keyword in device_battery_keywords):
            return self.tools_manager.get_device_info('battery', lang)
        if any(keyword in prompt_lower for keyword in realtime_keywords):
            for kw in realtime_keywords:
                if kw in prompt:
                    query = prompt.replace(kw, '').strip()
                    if not query:
                        query = prompt
                    return self.tools_manager.get_realtime_info(query, lang)
            return self.tools_manager.get_realtime_info(prompt, lang)
        return None
    def extract_city_from_prompt(self, prompt):
        cities = [
            '北京', '上海', '广州', '深圳', '成都', '重庆', '长沙', '东莞', '佛山', '杭州', '合肥', '南京', '宁波',
            '青岛', '苏州', '天津', '武汉', '西安', '郑州' '台北', '香港', '澳门','北海','保定', '长春', '常州', '大连',
            '福州', '贵阳', '哈尔滨', '海口', '合肥', '济南', '昆明', '兰州', '南昌', '南宁', '南通', '泉州', '石家庄', 
            '绍兴', '沈阳', '太原', '台州', '温州', '无锡', '厦门', '徐州', '烟台', '银川', '珠海', '洛阳', '潍坊'
        ]
        for city in cities:
            if city in prompt:
                return city
        return None
    def check_voice_switch(self, text):
        import random
        for k, v in self.voice_map.items():
            if f"切换到{k}" in text or f"{k}回答" in text or f"切换{k}" in text or f"用{k}回答" in text:
                if k == "普通话":
                    # 随机选择普通话音色
                    self.current_voice = random.choice(self.voice_map["普通话"])
                    return f"已切换到普通话（{self.current_voice}）"
                else:
                    self.current_voice = v
                    return f"已切换到{k}"
        return None
    def duplex(self):
        with self.client_lock:
            if self.client_active:
                return None
        try:
            data = self.vad_queue.get()

            vad_status = data.get("vad_statue")
            logger.debug(f"VAD队列数据: {vad_status}")
            if self.vad_start:
                self.speech.append(data)
                logger.debug(f"添加到语音缓冲区，当前长度: {len(self.speech)}")
            if vad_status is None:
                logger.debug("VAD状态为None，跳过处理")
                return None
            if "start" in vad_status:
                logger.info("检测到语音开始")
                self.vad_start = True
                self.speech.append(data)
            elif "end" in vad_status and len(self.speech) > 0:
                logger.info("检测到语音结束，开始处理语音")
                self.vad_start = False
                voice_data = [d["voice"] for d in self.speech]
                text,tts_url,tts_key = self.get_asr_text(voice_data)
                logger.info(f"语音识别结果: {text}")
                if len(text) >= 3:
                    print('user：', text)
                    self.speech = []
                    if "小七关机" in text or '关机关机' in text:
                        print("收到关机指令，切换到唤醒模式。")
                        self.wake_mode = True
                        self.player.play('recordings/ji.wav')
                        logger.info("小七关机")
                        return [0, "小七关机",None,None]
                    voice_switch_msg = self.check_voice_switch(text)
                    if voice_switch_msg:
                        print(voice_switch_msg)
                        self.player.play('recordings/10.wav')
                        logger.info('语言风格切换成功！')
                        return [0, voice_switch_msg,None,None]
                    if self.wake_mode:
                        if self.detect_wake_word(text):
                            print("唤醒成功，进入对话模式。")
                            logger.info("唤醒成功，进入对话模式。")
                            self.pause_recording()
                            random_number = random.randint(0, 3)
                            wav_path = os.path.join('recordings', str(random_number) + '.wav')
                            self.player.play(wav_path)
                            self.wait_for_playback_complete()
                            self.resume_recording()
                            self.wake_mode = False
                            self.last_active_time = time.time()
                        else:
                            print("未检测到唤醒词。")
                            self.player.play('recordings/5.wav')
                            logger.info("未检测到唤醒词。")
                        return [0, text,None,None]
                    else:
                        self.player.play('recordings/ding.wav')
                        self.last_active_time = time.time()
                        return [1, text,tts_url,tts_key]
                else:
                    logger.debug(f"语音识别结果太短: {text}")
                    self.speech = []
        except Exception as e:
            logger.error(f"duplex处理出错: {e}")
            return None
    def speak_and_play(self, answer_text, lang='zh'):
        if answer_text is None or len(answer_text) <= 0:
            logger.info(f"无需tts转换，query为空,{answer_text}")
            return None
        tts_file = self.tts.to_tts(answer_text, lang=lang)
        if tts_file is None:
            logger.error(f"tts转换失败,{answer_text}")
            return None
        self.player.play(tts_file)
        return tts_file
    def qwen_tts_play(self, answer_text,tts_url,tts_key):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
        responses = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
            model= tts_url,
            api_key= tts_key,
            text= answer_text,
            voice= self.current_voice,
            stream=True
        )
        for chunk in responses:
            audio_string = chunk["output"]["audio"]["data"]
            wav_bytes = base64.b64decode(audio_string)
            audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
            stream.write(audio_np.tobytes())
        time.sleep(0.8)
        stream.stop_stream()
        stream.close()
        p.terminate()
    def wait_for_playback_complete(self):
        self.player.wait_for_completion()
    def pause_recording(self):
        self.recording_paused = True
    def resume_recording(self):
        self.recording_paused = False

    async def text_to_speech(self,text, output_file="recordings/output.mp3", voice="zh-CN-XiaoxiaoNeural"):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(output_file)
        except Exception as e:
            print(f"⚠️ 生成失败: {str(e)}")
    def run(self):
        try:
            self.start_recording_and_vad()
            print('开始语音监听.......')
            logger.info('开始语音监听......')
            while not self.stop_event.is_set():
                if not self.wake_mode and (time.time() - self.last_active_time > 300):
                    print("5分钟无对话，回到唤醒模式。")
                    logger.info("5分钟无对话，回到唤醒模式。")
                    self.delete_all_files_if_more_than_ten('./tmp')
                    self.wake_mode = True
                status_text = self.duplex()
                if status_text is not None and status_text[0] == 1 and not self.wake_mode:
                    self.pause_recording()
                    answer_text = self.get_llm_answer(status_text[1])
                    print('AI:', answer_text)
                    logger.info(f"AI: {answer_text}")
                    self.qwen_tts_play(answer_text,status_text[2],status_text[3])
                    # self.speak_and_play(answer_text)
                    self.resume_recording()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Exiting...")
    def client_tts_play(self, text):
        self.pause_recording()
        self.speak_and_play(text)
        self.wait_for_playback_complete()
        self.resume_recording()
