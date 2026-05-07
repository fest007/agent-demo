"""
Edge-TTS 引擎实现

使用微软 Edge 的免费 TTS 服务。
优点：
- 完全免费，无需 API Key
- 中文音质极高（XiaoxiaoNeural 等）
- 支持多种语言和语音角色

使用 edge-tts 库，底层调用微软的 Neural TTS 服务。
"""
import edge_tts
import io
from agent.tts.engine import TTSEngine
from agent.config import get_settings


class EdgeTTSEngine(TTSEngine):
    """Edge-TTS 引擎（微软免费 TTS）"""

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """
        使用 Edge-TTS 合成语音

        edge_tts.Communicate 是异步生成器，
        通过 stream() 方法逐块获取音频数据。

        Args:
            text: 要转换的文本
            voice: 语音角色（如 "zh-CN-XiaoxiaoNeural"）

        Returns:
            MP3 音频数据
        """
        settings = get_settings()
        # 如果没有指定语音，使用配置文件中的默认值
        v = voice if voice != "default" else settings.tts_voice

        # 创建 Communicate 实例
        communicate = edge_tts.Communicate(text, v)

        # 逐块收集音频数据
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        return buffer.getvalue()

    def get_name(self) -> str:
        return "edge-tts"
