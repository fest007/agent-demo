"""
TTS 引擎抽象基类

定义了 TTS（Text-to-Speech）引擎的统一接口。
所有 TTS 引擎实现都必须继承这个类。

这种设计的好处：
- 上层代码只需要调用 TTSEngine 接口，不关心具体实现
- 可以随时切换 TTS 引擎（MiMo TTS ↔ Edge-TTS）
- 新增 TTS 引擎只需实现这个接口
"""
from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """TTS 引擎抽象基类"""

    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """
        将文本转为语音

        Args:
            text: 要转换的文本
            voice: 语音角色（如 "zh-CN-XiaoxiaoNeural"）

        Returns:
            音频数据（bytes），通常是 MP3 格式
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """获取引擎名称（如 "mimo-tts", "edge-tts"）"""
        ...
