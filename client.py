import sys
import time
import requests
import os
import base64
import cv2
import json
import numpy as np

def get_requests(url, data):
    """发送TTS请求"""
    try:
        resp = requests.post(url, json=data, timeout=30)
        resp.raise_for_status()  # 检查HTTP状态码
        get_json = resp.json()
        return get_json
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return None

def tts_play_text(text, url='http://127.0.0.1:10180/AI/voice/audio/tts_ply'):

    # ai_status = 1    # 语音播报功能开启
    # ai_status = 2  #语音对话功能开启
    # ai_status = 3  #语音对话功能关闭
    data = {'ai_text': text,'ai_status': 2}
    result = get_requests(url, data)
    return result


if __name__ == '__main__':
    text = '请不要在此地躺卧，立即离开!'
    result = tts_play_text(text)
    print(result)

    
