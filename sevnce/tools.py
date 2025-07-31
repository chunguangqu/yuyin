import requests
import json
import datetime
import lunardate
import time
from typing import Dict, Any, Optional
import logging


logger = logging.getLogger(__name__)

# 新增农历工具
class LunarTool:
    def get_lunar_info(self) -> str:
        try:
            # 生肖列表
            zodiacs = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
            # 天干和地支
            tiangan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
            dizhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
            # 获取当前公历日期
            today = datetime.date.today()
            year, month, day = today.year, today.month, today.day
            # 转换为农历日期
            lunar = lunardate.LunarDate.fromSolarDate(year, month, day)
            # 生肖计算（农历年）
            zodiac = zodiacs[(lunar.year - 4) % 12]
            # 干支年计算
            tg = tiangan[(lunar.year - 4) % 10]
            dz = dizhi[(lunar.year - 4) % 12]
            ganzhi = f"{tg}{dz}"
            return f"公历{year}年{month}月{day}日，农历{lunar.month}月{lunar.day}日，生肖{zodiac}，干支{ganzhi}年"
        except Exception as e:
            logger.error(f"农历API请求失败: {e}")
            return "农历信息获取失败。"



# 新增实时信息工具
class RealtimeInfoTool:
    def __init__(self):
        # 设置请求头和超时时间
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = 15  # 增加超时时间到15秒
        self.max_retries = 3  # 最大重试次数
        
    def _make_request_with_retry(self, url, max_retries=None):
        """带重试机制的请求"""
        if max_retries is None:
            max_retries = self.max_retries
            
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)  # 重试前等待1秒
        return None
    
    def _search_wikipedia(self, query, lang='zh'):
        """搜索维基百科"""
        try:
            if lang == 'zh':
                # 先查中文维基百科
                url = (
                    f'https://zh.wikipedia.org/w/api.php?'
                    f'action=query&prop=extracts&exintro&explaintext&format=json&titles={query}'
                )
                resp = self._make_request_with_retry(url)
                if resp:
                    data = resp.json()
                    pages = data.get('query', {}).get('pages', {})
                    for page in pages.values():
                        desc = page.get('extract', '')
                        if desc:
                            return desc[:60] + ("..." if len(desc) > 60 else "")
                
                # 若中文无结果，尝试英文
                url_en = (
                    f'https://en.wikipedia.org/w/api.php?'
                    f'action=query&prop=extracts&exintro&explaintext&format=json&titles={query}'
                )
                resp_en = self._make_request_with_retry(url_en)
                if resp_en:
                    data_en = resp_en.json()
                    pages_en = data_en.get('query', {}).get('pages', {})
                    for page in pages_en.values():
                        desc = page.get('extract', '')
                        if desc:
                            return desc[:60] + ("..." if len(desc) > 60 else "")
            else:
                # 先查英文维基百科
                url_en = (
                    f'https://en.wikipedia.org/w/api.php?'
                    f'action=query&prop=extracts&exintro&explaintext&format=json&titles={query}'
                )
                resp_en = self._make_request_with_retry(url_en)
                if resp_en:
                    data_en = resp_en.json()
                    pages_en = data_en.get('query', {}).get('pages', {})
                    for page in pages_en.values():
                        desc = page.get('extract', '')
                        if desc:
                            return desc[:60] + ("..." if len(desc) > 60 else "")
                
                # 若英文无结果，尝试中文
                url = (
                    f'https://zh.wikipedia.org/w/api.php?'
                    f'action=query&prop=extracts&exintro&explaintext&format=json&titles={query}'
                )
                resp = self._make_request_with_retry(url)
                if resp:
                    data = resp.json()
                    pages = data.get('query', {}).get('pages', {})
                    for page in pages.values():
                        desc = page.get('extract', '')
                        if desc:
                            return desc[:60] + ("..." if len(desc) > 60 else "")
        except Exception as e:
            logger.error(f"维基百科搜索失败: {e}")
        return None
    
    def _search_duckduckgo(self, query, lang='zh'):
        """使用DuckDuckGo搜索"""
        try:
            # 使用DuckDuckGo Instant Answer API
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            resp = self._make_request_with_retry(url)
            if resp:
                data = resp.json()
                if data.get('Abstract'):
                    return data['Abstract'][:60] + ("..." if len(data['Abstract']) > 60 else "")
                elif data.get('Answer'):
                    return data['Answer'][:60] + ("..." if len(data['Answer']) > 60 else "")
                elif data.get('RelatedTopics') and len(data['RelatedTopics']) > 0:
                    # 如果有相关主题，返回第一个
                    topic = data['RelatedTopics'][0]
                    if isinstance(topic, dict) and topic.get('Text'):
                        return topic['Text'][:60] + ("..." if len(topic['Text']) > 60 else "")
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
        return None
    
    def _search_baidu(self, query, lang='zh'):
        """使用百度搜索（备用方案）"""
        try:
            # 这里可以集成百度搜索API，目前返回简单信息
            if lang == 'zh':
                return f"正在搜索关于'{query}'的信息..."
            else:
                return f"Searching for information about '{query}'..."
        except Exception as e:
            logger.error(f"百度搜索失败: {e}")
        return None
    
    def _search_bing(self, query, lang='zh'):
        """使用Bing搜索（备用方案）"""
        try:
            # 使用Bing搜索API（需要API密钥）
            # 这里提供一个简化的实现
            if lang == 'zh':
                return f"正在通过Bing搜索'{query}'的相关信息..."
            else:
                return f"Searching for '{query}' information via Bing..."
        except Exception as e:
            logger.error(f"Bing搜索失败: {e}")
        return None
    
    def _search_google(self, query, lang='zh'):
        """使用Google搜索（备用方案）"""
        try:
            # 使用Google搜索API（需要API密钥）
            # 这里提供一个简化的实现
            if lang == 'zh':
                return f"正在通过Google搜索'{query}'的相关信息..."
            else:
                return f"Searching for '{query}' information via Google..."
        except Exception as e:
            logger.error(f"Google搜索失败: {e}")
        return None
    
    def get_realtime_info(self, query: str, lang: str = 'zh') -> str:
        """获取实时信息，使用多个数据源"""
        try:
            # 1. 首先尝试维基百科
            result = self._search_wikipedia(query, lang)
            if result:
                return result
            
            # 2. 如果维基百科失败，尝试DuckDuckGo
            result = self._search_duckduckgo(query, lang)
            if result:
                return result
            
            # 3. 尝试Bing搜索
            result = self._search_bing(query, lang)
            if result:
                return result
            
            # 4. 尝试Google搜索
            result = self._search_google(query, lang)
            if result:
                return result
            
            # 5. 最后使用百度搜索作为备用
            result = self._search_baidu(query, lang)
            if result:
                return result
            
            # 6. 如果所有方法都失败
            if lang == 'zh':
                return "抱歉，暂时无法获取相关信息，请稍后再试。"
            else:
                return "Sorry, unable to get relevant information at the moment, please try again later."
                
        except Exception as e:
            logger.error(f"实时信息API请求失败: {e}")
            if lang == 'zh':
                return "网络连接超时，请检查网络后重试。"
            else:
                return "Network connection timeout, please check your network and try again."

class WeatherTool:
    def __init__(self, config=None):        
        # 备用的免费天气API
        self.fallback_url = "https://wttr.in"
        
    def get_weather(self, city: str, lang: str = 'zh', date: str = None) -> Dict[str, Any]:
        # 如果date不是今天，返回友好提示
        if date:
            try:
                today = datetime.date.today()
                if isinstance(date, str):
                    query_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
                else:
                    query_date = date
                if query_date != today:
                    return {'error': '暂不支持历史或未来天气查询，仅支持当天实时天气。' if lang == 'zh' else 'Sorry, only real-time weather for today is supported.'}
            except Exception:
                return {'error': '日期格式错误，请用YYYY-MM-DD格式。' if lang == 'zh' else 'Date format error, please use YYYY-MM-DD.'}
        try:
            # Base URL for OpenWeatherMap API
            base_url = "http://api.openweathermap.org/data/2.5/weather"
            # Parameters for the API call
            params = {
                'q': city,  # City name
                'appid': "08d09a1507931f2c20dd3ac7260069b5",  # Your API key
                'units': 'metric',  # Units in metric (Celsius)
                'lang': lang if lang in ['zh', 'en'] else 'zh'  # Language of the results
            }
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            data = response.json()
            weather_info = {
                    'city': city,
                    'country': 'CN',
                    'temperature': int(data['main']['temp']),
                    'description': data['weather'][0]['description']
                }
            return weather_info
        
        except requests.exceptions.RequestException as e:
            logger.error(f"天气API请求失败: {e}")
     

        try:
            params = {
                'q': city,
                'format': 'j1',  # JSON格式
                'lang': lang if lang in ['zh', 'en'] else 'zh'     # 中文
            }

            response = requests.get(self.fallback_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'current_condition' in data and len(data['current_condition']) > 0:
                current = data['current_condition'][0]
                desc = current['lang_zh'][0]['value'] if lang == 'zh' else current.get('weatherDesc', [{'value': ''}])[0]['value']
                weather_info = {
                    'city': city,
                    'country': 'CN',
                    'temperature': int(current['temp_C']),
                    'description': desc,
                }
                return weather_info
            else:
                return {'error': '无法获取天气信息' if lang == 'zh' else 'Failed to get weather info'}

        except requests.exceptions.RequestException as e:
            logger.error(f"备用天气API请求失败: {e}")
            return {'error': '网络连接失败，请检查网络' if lang == 'zh' else 'Network connection failed, please check your network'}
        except Exception as e:
            logger.error(f"获取天气信息时出错: {e}")
            return {'error': '获取天气信息时出现未知错误' if lang == 'zh' else 'Unknown error occurred while getting weather info'}

class TimeTool:
    def get_current_time(self, lang: str = 'zh') -> Dict[str, str]:
        now = datetime.datetime.now()
        
        if lang == 'zh':
            time_info = {
                'time': now.strftime('%H:%M:%S'),
                'date': now.strftime('%Y年%m月%d日'),
                'weekday': self._get_weekday_cn(now.weekday()),
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'hour': now.hour,
                'minute': now.minute,
                'second': now.second
            }
        else:
            time_info = {
                'time': now.strftime('%H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'weekday': self._get_weekday_en(now.weekday()),
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'hour': now.hour,
                'minute': now.minute,
                'second': now.second
            }
        
        return time_info
    
    def _get_weekday_cn(self, weekday: int) -> str:
        """将星期数字转换为中文"""
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[weekday]
    def _get_weekday_en(self, weekday: int) -> str:
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return weekdays[weekday]

class DEVICE_TOOL:

    def get_requests(self, url, data):
        # 发送请求
        resp = requests.post(url, data=data)
        get_json = resp.json()
        res = get_json
        return res

    def get_robot_info(self,ai_status):
        # ai_status = 'VOICE_REQ_04'   #查询气体浓度
        # ai_status = 'VOICE_REQ_07'   # 查询导航状态
        # ai_status = 'VOICE_REQ_09'   #'查询剩余电量'
        output_text = self.get_requests('http://192.168.1.175:8883/voice/control',ai_status)
        result = output_text['dataMsg']
        return result

class ToolsManager:
    def __init__(self, config=None):
        self.weather_tool = WeatherTool(config)
        self.time_tool = TimeTool()
        self.lunar_tool = LunarTool()
        self.realtime_tool = RealtimeInfoTool()
        self.robot_tool = DEVICE_TOOL()
        
    def get_weather_info(self, city_pinyin: str, lang: str = 'zh', date: str = None) -> str:
        weather_data = self.weather_tool.get_weather(city_pinyin, lang, date)
        
        if 'error' in weather_data:
            return "抱歉，获取天气信息失败了." if lang == 'zh' else "Sorry, failed to get weather information."
        if lang == 'zh':
            weather_text = (
                f"天气{weather_data['description']},"
                f"温度{weather_data['temperature']}摄氏度"
            )
        else:
            weather_text = (
                f"Weather: {weather_data['description']}, "
                f"Temperature: {weather_data['temperature']}Celsius"
            )
        return weather_text
    
    def get_time_info(self, lang: str = 'zh') -> str:
        time_data = self.time_tool.get_current_time(lang)
        
        if lang == 'zh':
            time_text = (
                f"现在是{time_data['date']}，"
                f"{time_data['weekday']}，"
                f"时间{time_data['time']}。"
            )
        else:
            time_text = (
                f"Now is {time_data['date']}, "
                f"{time_data['weekday']}, "
                f"Time {time_data['time']}."
            )
        return time_text
    
    def get_date_info(self, lang: str = 'zh') -> str:
        time_data = self.time_tool.get_current_time(lang)
        if lang == 'zh':
            date_text = f"今天是{time_data['date']}，{time_data['weekday']}。"
        else:
            date_text = f"Today is {time_data['date']}, {time_data['weekday']}."
        return date_text 

    # 新增：获取农历年、生肖、干支年
    def get_lunar_info(self) -> str:
        return self.lunar_tool.get_lunar_info()

    # 新增：实时信息查询
    def get_realtime_info(self, query: str, lang: str = 'zh') -> str:
        return self.realtime_tool.get_realtime_info(query, lang)

    # 新增：设备信息查询
    def get_device_info(self, info_type: str, lang: str = 'zh') -> str:
        # info_type: gas, nav, battery
        ai_status_map = {
            'gas': 'VOICE_REQ_04',
            'nav': 'VOICE_REQ_07',
            'battery': 'VOICE_REQ_09',
        }
        ai_status = ai_status_map.get(info_type)
        if not ai_status:
            return "暂不支持该设备信息查询。" if lang == 'zh' else "This device info is not supported."
        try:
            result = self.robot_tool.get_robot_info({'ai_status': ai_status})
            if lang == 'zh':
                if info_type == 'gas':
                    return f"气体浓度：{result}"
                elif info_type == 'nav':
                    return f"导航状态：{result}"
                elif info_type == 'battery':
                    return f"剩余电量：{result}"
            else:
                if info_type == 'gas':
                    return f"Gas concentration: {result}"
                elif info_type == 'nav':
                    return f"Navigation status: {result}"
                elif info_type == 'battery':
                    return f"Battery left: {result}"
        except Exception as e:
            logger.error(f"设备信息API请求失败: {e}")
            return "设备信息获取失败。" if lang == 'zh' else "Failed to get device info."



