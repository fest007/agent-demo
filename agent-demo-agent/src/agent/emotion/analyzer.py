"""
情绪分析模块

使用 LLM 的结构化输出能力判断用户情绪。
将用户消息发送给 LLM，让它返回一个预定义的情绪标签。

情绪标签：
- happy: 开心
- sad: 难过
- angry: 生气
- anxious: 焦虑
- confused: 困惑
- neutral: 平静（默认）
- excited: 兴奋
"""
from langchain_core.language_models import BaseChatModel
from agent.prompts import EMOTION_PROMPT

# 有效的情绪标签集合，用于验证 LLM 输出
VALID_EMOTIONS = {"happy", "sad", "angry", "anxious", "confused", "neutral", "excited"}


async def analyze_emotion(llm: BaseChatModel, message: str) -> str:
    """
    分析用户消息的情绪

    工作原理：
    1. 将用户消息填入情绪分析提示词模板
    2. 发送给 LLM
    3. 解析 LLM 返回的情绪标签
    4. 如果标签无效，默认返回 "neutral"

    Args:
        llm: 大语言模型实例
        message: 用户消息文本

    Returns:
        情绪标签字符串
    """
    try:
        # 填充提示词模板
        prompt = EMOTION_PROMPT.format(message=message)

        # 调用 LLM 分析情绪
        response = await llm.ainvoke(prompt)

        # 解析并验证结果
        emotion = response.content.strip().lower()
        if emotion in VALID_EMOTIONS:
            return emotion
        return "neutral"  # LLM 返回了无效标签，降级为 neutral
    except Exception:
        # 分析失败不影响对话，默认为平静
        return "neutral"
