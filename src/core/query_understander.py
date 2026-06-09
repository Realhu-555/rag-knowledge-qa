"""查询理解"""
import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from src.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_TEMPERATURE,
)


@dataclass
class QueryExpansion:
    """查询扩展结果"""
    original_query: str
    expanded_queries: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    intent: str = ""


class QueryUnderstander:
    """查询理解器"""

    def __init__(self):
        self.client = None

    def _init_client(self):
        """初始化DeepSeek客户端"""
        if self.client is None:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL
            )

    def expand_query(self, query: str) -> QueryExpansion:
        """查询扩展：把问题拆成多个子查询"""
        self._init_client()

        prompt = f"""请将以下用户问题拆分成3-5个不同角度的子查询，用于检索知识库。

用户问题：{query}

请返回JSON格式：
{{
    "expanded_queries": ["子查询1", "子查询2", "子查询3"],
    "entities": ["实体1", "实体2"],
    "intent": "用户意图描述"
}}

要求：
1. 子查询要覆盖问题的不同方面
2. 实体包括人名、地名、专业术语等
3. 意图要简洁明了"""

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个查询分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=500
            )

            result_text = response.choices[0].message.content

            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return QueryExpansion(
                        original_query=query,
                        expanded_queries=result.get("expanded_queries", [query]),
                        entities=result.get("entities", []),
                        intent=result.get("intent", "")
                    )
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return QueryExpansion(
            original_query=query,
            expanded_queries=[query],
            entities=[],
            intent=""
        )

    def generate_hyde(self, query: str) -> str:
        """HyDE：生成假设性文档"""
        self._init_client()

        prompt = f"""请基于以下问题，生成一段假设性的回答（像知识库中会有的内容）。

问题：{query}

要求：
1. 假设性回答应该像文档中的内容，而不是对话式的回答
2. 包含可能相关的关键词和信息
3. 长度约100-200字"""

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个文档生成专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=300
            )
            return response.choices[0].message.content

        except Exception:
            return query
