"""意图识别 — 判断用户当前轮的意图"""
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI

from src.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)


class Intent(str, Enum):
    """用户意图类型"""
    QUERY = "query"          # 知识查询 → 走RAG
    FOLLOWUP = "followup"    # 追问 → 基于上轮回答继续深入
    CHITCHAT = "chitchat"    # 闲聊 → 直接LLM回答
    FEEDBACK = "feedback"    # 反馈 → 记录


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: Intent
    confidence: float = 1.0


class IntentClassifier:
    """用LLM判断用户意图"""

    _KEYWORDS_CHITCHAT = {
        "你好", "你是谁", "谢谢", "好的", "明白了", "再见",
        "请问你", "帮我", "讲个笑话",
    }
    _KEYWORDS_FEEDBACK = {
        "不对", "错误", "不准确", "没用", "这个回答", "你说的不对",
        "回答错了", "不太对", "不是这样",
    }

    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

    def classify(self, question: str, has_history: bool = False) -> IntentResult:
        """判断用户意图。

        先用关键词快速判断，判断不了再调LLM。

        Args:
            question: 用户当前轮的问题
            has_history: 是否有对话历史

        Returns:
            IntentResult
        """
        # 快速关键词匹配
        q = question.strip()

        # 反馈意图（通常较短、含负面词）
        if any(kw in q for kw in self._KEYWORDS_FEEDBACK):
            return IntentResult(intent=Intent.FEEDBACK, confidence=0.8)

        # 闲聊意图（无历史时的简单问候等）
        if not has_history:
            if any(kw in q for kw in self._KEYWORDS_CHITCHAT):
                return IntentResult(intent=Intent.CHITCHAT, confidence=0.8)

        # 无法快速判断时调LLM
        return self._classify_with_llm(question, has_history)

    def _classify_with_llm(self, question: str, has_history: bool) -> IntentResult:
        """用LLM进行意图分类"""
        context_hint = "用户正在进行多轮对话。" if has_history else "这是对话的第一轮。"

        prompt = (
            f"请判断用户的意图类型。{context_hint}\n\n"
            f"用户输入：{question}\n\n"
            "可选意图：\n"
            "- query：用户想查询知识库中的信息（技术问题、概念解释、文档内容等）\n"
            "- followup：用户在追问上一轮回答的细节或延伸\n"
            "- chitchat：用户在闲聊（问候、感谢、无关话题等）\n"
            "- feedback：用户在对之前的回答给出反馈（对/不对、好评/差评）\n\n"
            "只回复意图类型名称（query/followup/chitchat/feedback），不要解释。"
        )

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=20,
            )
            raw = response.choices[0].message.content.strip().lower()

            # 解析结果
            for intent in Intent:
                if intent.value in raw:
                    return IntentResult(intent=intent, confidence=0.9)

            # 无法解析时默认为query
            return IntentResult(intent=Intent.QUERY, confidence=0.5)

        except Exception:
            # LLM调用失败时默认走RAG
            return IntentResult(intent=Intent.QUERY, confidence=0.5)
