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
                  history: list[dict] | None = None,
                  summary: str = "") -> dict:
        """生成回答

        Args:
            question: 用户当前问题
            sources: 检索到的参考资料列表
            history: 对话历史，格式 [{"role": "user/assistant", "content": "..."}]
            summary: M8: 对话摘要，注入system message
        """
        self._init_client()

        prompt = self._build_prompt(question, sources)

        # 构建系统提示
        system_content = (
            "你是知识库问答助手。请基于参考资料和对话历史回答。\n"
            "引用格式：在关键论断末尾标注（文件名，章节名）。\n"
            "如果用户追问（如详细一点、展开说说），结合对话上下文理解意图，"
            "优先从参考资料查找，找不到则基于之前的回答展开。"
        )
        if summary:
            system_content += f"\n\n之前对话的摘要：\n{summary}"

        # 构建消息列表：系统提示 + 历史对话 + 当前问题
        messages = [
            {"role": "system", "content": system_content},
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
1. 优先使用参考资料中的信息回答问题
2. 如果参考资料中有相关信息，基于参考资料回答
3. 如果参考资料中没有，但对话历史中有相关内容（比如之前的回答中出现过），可以基于对话历史回答，并说明"基于之前的对话内容"
4. 只有参考资料和对话历史都无法回答时，才说"知识库中未找到相关信息"
5. 多个来源支持同一论断时，全部标注

引用格式：
在每个关键论断的末尾标注来源，格式为：（文件名，第X页）或（文件名，XX章节）
示例：FastAPI是当前最流行的Python Web框架之一（AI技术栈介绍.md，第3页）
如果无法确定具体页码，用章节名代替：FastAPI专为API开发设计（AI技术栈介绍.md，Web框架章节）

参考资料：
"""
        for i, source in enumerate(sources, 1):
            meta = source.get("metadata", {})
            file_name = meta.get("source_file", "") or meta.get("source", "未知")
            if "\\" in file_name or "/" in file_name:
                file_name = file_name.replace("\\", "/").split("/")[-1]
            section = meta.get("section", "")
            page = meta.get("page_number", "")
            content = source.get("content", "")
            source_tag = file_name
            if page:
                source_tag += f"，第{page}页"
            elif section:
                source_tag += f"，{section}"
            prompt += f"[{source_tag}] {content}\n\n"

        prompt += f"用户问题：{question}"

        return prompt
