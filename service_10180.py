# -*- coding: UTF-8 -*-
from sevnce.robot import Robot
from sevnce.utils import read_config
from loggers import update_log_level
import threading
from flask import Flask, request, jsonify

# 创建Flask应用
app = Flask(__name__)

# 全局变量存储robot实例
robot_instance = None

@app.route('/AI/voice/audio/tts_ply', methods=['POST'])
def tts_play():
    """处理客户端TTS播报和语音对话控制请求"""
    try:
        data = request.get_json()
        if not data or 'ai_status' not in data:
            return jsonify({"statusCode": 0, "statusMsg": "缺少ai_status参数", "result": {"array": [125]}})

        ai_status = data['ai_status']
        # ai_status=1: 只允许TTS播报
        if ai_status == 1:
            if 'ai_text' not in data or not data['ai_text'] or len(data['ai_text'].strip()) == 0:
                return jsonify({"statusCode": 0, "statusMsg": "缺少或空的ai_text参数", "result": {"array": [125]}})
            text = data['ai_text']
            robot_instance.pause_recording()  # 确保语音对话关闭
            robot_instance.client_tts_play(text)
            return jsonify({"statusCode": 1, "statusMsg": "语音播报成功!", "result": {"array": [121]}})
        # ai_status=2: 开启语音对话
        elif ai_status == 2:
            try:
                robot_instance.resume_recording()
                robot_instance.wake_mode = True  # 进入唤醒等待状态
                return jsonify({"statusCode": 1, "statusMsg": "语音对话功能已开启，等待唤醒词", "result": {"array": [121]}})
            except Exception as e:
                return jsonify({"statusCode": 0, "statusMsg": f"开启语音对话失败: {str(e)}", "result": {"array": [125]}})
        # ai_status=3: 关闭语音对话
        elif ai_status == 3:
            try:
                robot_instance.pause_recording()
                return jsonify({"statusCode": 1, "statusMsg": "语音对话功能已关闭", "result": {"array": [121]}})
            except Exception as e:
                return jsonify({"statusCode": 0, "statusMsg": f"关闭语音对话失败: {str(e)}", "result": {"array": [125]}})
        else:
            return jsonify({"statusCode": 0, "statusMsg": "未知ai_status参数", "result": {"array": [125]}})

    except Exception as e:
        return jsonify({"statusCode": 0,"statusMsg": f"服务器内部错误: {str(e)}","result": {"array": [125]}})

def start_flask_server():
    """启动Flask服务器"""
    app.run(host='0.0.0.0', port=10180, debug=False, use_reloader=False)

if __name__ == "__main__":
    config_file = "config/config.yaml"
    
    # 读取配置文件
    config = read_config(config_file)
    
    # 设置日志级别
    log_level = config.get("logging", {}).get("level", "info")
    update_log_level(log_level)
    print(f"日志级别设置为: {log_level}")
    
    # 创建机器人实例
    robot_instance = Robot(config_file)
    
    # 启动HTTP服务器线程
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()

    # 启动语音对话机器人
    robot_instance.run()
    
    

