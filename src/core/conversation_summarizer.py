"""对话摘要 — 当对话超长时压缩历史"""
from openai import OpenAI

from src.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    SUMMARY_THRESHOLD_ROUNDS,
    SUMMARY_KEEP_RECENT_ROUNDS,
)


class ConversationSummarizer:
    """用LLM将长对话历史压缩为摘要"""

    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

    def summarize(self, messages: list[dict]) -> str:
        """将对话消息列表压缩为一段摘要文本。

        Args:
            messages: 完整对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            摘要字符串
        """
        if not messages:
            return ""

        # 格式化对话内容
        conversation_text = ""
        for msg in messages:
            role_label = "用户" if msg["role"] == "user" else "助手"
            conversation_text += f"{role_label}: {msg['content']}\n\n"

        prompt = (
            "请将以下对话压缩为一段简洁的摘要，保留关键信息和上下文。"
            "摘要应该让后续的AI助手能够理解之前对话的脉络和要点。\n\n"
            f"对话内容：\n{conversation_text}\n"
            "摘要："
        )

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # 摘要失败时降级处理：返回简单的文本截断
            return f"[摘要生成失败: {e}] 对话包含 {len(messages)} 条消息"

    def split_messages(
        self,
        messages: list[dict],
        threshold_rounds: int = SUMMARY_THRESHOLD_ROUNDS,
        keep_recent: int = SUMMARY_KEEP_RECENT_ROUNDS,
    ) -> tuple[list[dict], list[dict]]:
        """将消息拆分为需要摘要的部分和保留的最近部分。

        Args:
            messages: 完整对话历史
            threshold_rounds: 超过多少轮（user+assistant为一轮）触发摘要
            keep_recent: 保留最近几轮

        Returns:
            (messages_to_summarize, messages_to_keep)
        """
        threshold_messages = threshold_rounds * 2  # 每轮2条消息
        keep_messages = keep_recent * 2

        if len(messages) <= threshold_messages:
            return [], messages

        split_point = len(messages) - keep_messages
        return messages[:split_point], messages[split_point:]
