"""
情绪反馈策略模块

根据用户的情绪标签，生成对应的回复风格指令。
这个指令会被注入到系统提示词中，引导 LLM 调整回复语气。

例如：
- 用户生气时 → Agent 保持冷静，承认问题，提供方案
- 用户难过时 → Agent 表达共情，温和安慰
- 用户困惑时 → Agent 用简单语言逐步引导
"""

# 每种情绪对应的回复风格指令
EMOTION_STYLES = {
    "happy": "用积极、轻松的语气回应，适当表达认同和赞赏。",
    "sad": "用温和、共情的语气回应，表达理解和支持。",
    "angry": "用冷静、理性的语气回应，承认问题并提供解决方案。",
    "anxious": "用耐心、确定的语气回应，提供清晰的信息和步骤。",
    "confused": "用简单、逐步引导的方式回应，避免复杂表述。",
    "neutral": "用专业、清晰的语气回应。",
    "excited": "用同频、积极的语气回应，支持用户的想法。",
}


def get_emotion_style(emotion: str) -> str:
    """
    获取情绪对应的回复风格指令

    Args:
        emotion: 情绪标签

    Returns:
        回复风格指令文本
    """
    return EMOTION_STYLES.get(emotion, EMOTION_STYLES["neutral"])


def build_emotion_context(emotion: str) -> str:
    """
    构建情绪上下文，用于注入系统提示词

    生成格式：\n当前用户情绪: happy。用积极、轻松的语气回应...

    Args:
        emotion: 情绪标签

    Returns:
        情绪上下文文本
    """
    style = get_emotion_style(emotion)
    return f"\n当前用户情绪: {emotion}。{style}"
