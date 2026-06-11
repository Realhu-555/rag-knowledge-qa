"""LLM生成"""
from openai import OpenAI

from src.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)


class Generator:
    """LLM回答生成器"""

    def __init__(self):
        self.client = None

    def _init_client(self):
        """初始化DeepSeek客户端"""
        if self.client is None:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL
            )

    def generate(self, question: str, sources: list[dict],
                  history: list[dict] | None = None) -> dict:
        """生成回答

        Args:
            question: 用户当前问题
            sources: 检索到的参考资料列表
            history: 对话历史，格式 [{"role": "user/assistant", "content": "..."}]
        """
        self._init_client()

        prompt = self._build_prompt(question, sources)

        # 构建消息列表：系统提示 + 历史对话 + 当前问题
        messages = [
            {"role": "system", "content": "你是知识库问答助手。请严格基于参考资料回答。"},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS
            )

            answer = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            return {"answer": answer, "usage": usage}

        except Exception as e:
            return {
                "answer": "抱歉，AI服务暂时不可用，请稍后重试。",
                "usage": {},
                "error": str(e)
            }

    def _build_prompt(self, question: str, sources: list[dict]) -> str:
        """构建prompt模板"""
        prompt = """规则：
1. 每个关键论断后面用[编号]标注引用来源
2. 只使用参考资料中的信息，不要编造
3. 如果参考资料不足以回答，说"知识库中未找到相关信息"
4. 多个来源支持同一论断时，全部标注：[1][3]

参考资料：
"""
        for i, source in enumerate(sources, 1):
            file_name = source.get("metadata", {}).get("source", "未知")
            section = source.get("metadata", {}).get("section", "")
            content = source.get("content", "")
            prompt += f"[{i}] 来源：{file_name} - {section}\n    内容：{content}\n\n"

        prompt += f"用户问题：{question}"

        return prompt
