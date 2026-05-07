"""
MiMo TTS 引擎实现

使用小米 MiMo 的 TTS API（mimo-v2.5-tts）进行语音合成。
目前限时免费，与 LLM 同平台，调用方式兼容 OpenAI TTS API。
"""
import httpx
from agent.tts.engine import TTSEngine
from agent.config import get_settings


class MiMoTTSEngine(TTSEngine):
    """MiMo TTS 引擎"""

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """
        调用 MiMo TTS API 合成语音

        API 端点：{base_url}/audio/speech
        请求格式：兼容 OpenAI TTS API

        Args:
            text: 要转换的文本
            voice: 语音角色

        Returns:
            MP3 音频数据
        """
        settings = get_settings()

        # 构建请求头（Bearer Token 认证）
        headers = {
            "Authorization": f"Bearer {settings.mimo_api_key}",
            "Content-Type": "application/json",
        }

        # 构建请求体
        payload = {
            "model": settings.tts_mimo_model,  # "mimo-v2.5-tts"
            "input": text,                      # 要合成的文本
            "voice": voice if voice != "default" else settings.tts_voice,
        }

        # 发送 POST 请求到 TTS API
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.mimo_base_url}/audio/speech",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.content  # 返回音频二进制数据

    def get_name(self) -> str:
        return "mimo-tts"
