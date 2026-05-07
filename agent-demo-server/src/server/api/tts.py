"""
TTS 语音合成 API 模块

提供文本转语音接口：
- POST /api/tts: 将文本转为 MP3 音频

支持两种引擎：
- mimo-tts: MiMo 自带 TTS（限时免费）
- edge-tts: 微软 Edge TTS（免费，中文质量高）
"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from server.deps import get_current_user, UserContext

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSRequest(BaseModel):
    """TTS 请求模型"""
    text: str          # 要转换的文本
    voice: str = "default"   # 语音角色
    engine: str = "edge-tts" # TTS 引擎（mimo-tts 或 edge-tts）


@router.post("")
async def text_to_speech(
    request: TTSRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    文本转语音

    根据指定的引擎调用对应的 TTS 服务，
    返回 MP3 格式的音频数据。

    Args:
        request: 包含 text, voice, engine

    Returns:
        MP3 音频二进制数据
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "agent-demo-agent" / "src"))
    from agent.tts.edge_tts import EdgeTTSEngine
    from agent.tts.mimo_tts import MiMoTTSEngine

    try:
        # 根据 engine 参数选择 TTS 引擎
        engine = MiMoTTSEngine() if request.engine == "mimo-tts" else EdgeTTSEngine()
        audio = await engine.synthesize(request.text, request.voice)
        # 返回音频数据，media_type 指定为 MP3
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        return Response(content=str(e), status_code=500)
