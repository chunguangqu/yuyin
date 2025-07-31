# 小七语音对话助手

一个基于Python开发的智能语音对话系统，集成了语音识别、语音合成、自然语言处理等功能，支持多语言对话和工具调用。

## 主要功能

### 🎤 语音交互
- **语音识别 (ASR)**: 使用FunASR进行实时语音转文字
- **语音合成 (TTS)**: 使用Edge TTS进行文字转语音
- **语音活动检测 (VAD)**: 使用Silero VAD进行语音端点检测
- **多语言支持**: 支持中文、英文、日文、韩文等多种语言

### 🤖 智能对话
- **大语言模型**: 集成Qwen3-8B模型进行自然语言理解
- **角色设定**: 设定为上海外滩景区服务型机器人"小七"
- **上下文理解**: 支持多轮对话和上下文记忆

### 🛠️ 工具调用
- **时间查询**: 获取当前时间
- **日期查询**: 获取当前日期和星期
- **天气查询**: 查询指定城市的天气信息
- **设备状态**: 查询设备运行状态

### 📚 知识库
- **本地RAG**: 基于本地知识库的问答系统
- **景区信息**: 包含外滩景区相关信息和问答
- **公司信息**: 七腾机器人有限公司相关信息

### 🌐 Web服务
- **HTTP API**: 提供RESTful API接口
- **客户端支持**: 支持外部客户端调用TTS和对话功能
- **状态控制**: 支持开启/关闭语音对话功能

## 系统架构

```
├── client.py              # 客户端示例代码
├── service_10180.py       # Web服务主程序
├── sevnce/                # 核心服务模块
│   ├── robot.py          # 机器人主控制器
│   ├── asr.py            # 语音识别模块
│   ├── tts.py            # 语音合成模块
│   ├── vad.py            # 语音活动检测
│   ├── recorder.py       # 音频录制模块
│   ├── player.py         # 音频播放模块
│   ├── rag.py            # 知识库检索模块
│   ├── tools.py          # 工具调用管理
│   └── utils.py          # 工具函数
├── config/               # 配置文件
│   ├── config.yaml       # 主配置文件
│   └── alsa.conf         # 音频配置
├── info/                 # 知识库文件
│   └── knowledge.txt     # 问答知识库
├── recordings/           # 录音文件目录
└── tmp/                 # 临时文件目录
```

## 环境要求

### 系统要求
- Python 3.8+
- Windows/Linux/macOS
- 麦克风和扬声器设备

### Python依赖包

```bash
pip install -r requirements.txt
```

主要依赖包包括：
- `pyaudio>=0.2.11` - 音频处理
- `pygame>=2.0.0` - 音频播放
- `numpy>=1.21.0` - 数值计算
- `requests>=2.25.0` - HTTP请求
- `pyyaml>=5.4.0` - YAML配置文件解析
- `edge-tts>=6.1.0` - Edge TTS语音合成
- `funasr>=0.10.0` - 语音识别
- `torch>=1.9.0` - PyTorch深度学习框架
- `torchaudio>=0.9.0` - 音频处理
- `scipy>=1.7.0` - 科学计算
- `langdetect>=1.0.9` - 语言检测

## 安装和配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd yuyin
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置音频设备
确保系统有可用的麦克风和扬声器设备。

### 4. 修改配置文件
编辑 `config/config.yaml` 文件，根据需要调整以下配置：

```yaml
# 唤醒词设置
wake_word: 你好小七

# 语音识别服务地址
FUNASR:
    url: http://your-funasr-server:port/AI/voice/audio/funasr

# 大语言模型配置
LLM:
    model_name: Qwen3-8B
    url: http://your-llm-server:port/v1
    api_key: your-api-key

# 天气API配置
Weather:
    api_key: your-weather-api-key
    base_url: http://api.openweathermap.org/data/2.5/weather
```

## 使用方法

### 启动服务

1. **启动主服务**
```bash
python service_10180.py
```

2. **启动客户端测试**
```bash
python client.py
```

### API接口

#### TTS播报和对话控制
- **URL**: `http://localhost:10180/AI/voice/audio/tts_ply`
- **方法**: POST
- **参数**:
  - `ai_text`: 要播报的文本
  - `ai_status`: 控制状态
    - `1`: 只允许TTS播报
    - `2`: 开启语音对话
    - `3`: 关闭语音对话

#### 示例请求
```python
import requests

# TTS播报
data = {
    'ai_text': '你好，我是小七！',
    'ai_status': 1
}
response = requests.post('http://localhost:10180/AI/voice/audio/tts_ply', json=data)

# 开启语音对话
data = {'ai_status': 2}
response = requests.post('http://localhost:10180/AI/voice/audio/tts_ply', json=data)
```

### 语音交互

1. **唤醒**: 说出唤醒词"你好小七"
2. **对话**: 系统进入对话模式，可以询问天气、时间、景区信息等
3. **结束**: 系统会自动检测静音并结束对话

## 功能特性

### 🎯 智能对话
- 支持多轮对话和上下文理解
- 自动语言检测和回复
- 友好的口语化回复风格

### 🔧 工具集成
- 时间日期查询
- 实时天气信息
- 设备状态监控
- 本地知识库检索

### 🎵 音频处理
- 高质量语音合成
- 实时语音识别
- 智能语音端点检测
- 多格式音频支持

### 🌍 多语言支持
- 中文（普通话、北京话、上海话、四川话）
- 英文
- 日文
- 韩文

## 配置说明

### 音频配置
- **采样率**: 16000Hz
- **VAD阈值**: 0.5
- **静音检测**: 200ms

### 语音合成配置
- **默认语音**: zh-CN-XiaoxiaoNeural
- **流式输出**: 启用
- **块大小**: 4096字节

### 日志配置
- **日志级别**: info
- **日志文件**: 自动生成

## 故障排除

### 常见问题

1. **音频设备问题**
   - 检查麦克风和扬声器连接
   - 确认系统音频权限
   - 检查PyAudio安装

2. **网络连接问题**
   - 确认FunASR服务可访问
   - 检查LLM服务连接
   - 验证API密钥有效性

3. **依赖包问题**
   - 重新安装requirements.txt
   - 检查Python版本兼容性
   - 更新pip和setuptools

### 日志查看
系统运行时会生成详细日志，可通过日志文件查看运行状态和错误信息。

## 开发说明

### 模块扩展
- 新增TTS引擎: 在`sevnce/tts.py`中添加新类
- 新增ASR引擎: 在`sevnce/asr.py`中添加新类
- 新增工具: 在`sevnce/tools.py`中扩展ToolsManager

### 知识库更新
编辑`info/knowledge.txt`文件，按以下格式添加问答对：
```
question：问题内容
answer：答案内容
```

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题或建议，请联系开发团队。 