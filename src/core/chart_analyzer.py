"""图表分析器：识别图表类型、提取数据、生成结构化描述"""
from src.config import (
    CHART_ANALYSIS_ENABLED,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)


class ChartAnalyzer:
    """图表分析器"""

    # 已知图表类型关键词
    CHART_KEYWORDS = {
        "bar": ["柱状图", "条形图", "柱形", "bar chart", "bar graph"],
        "line": ["折线图", "趋势图", "曲线图", "line chart", "line graph"],
        "pie": ["饼图", "扇形图", "占比", "pie chart", "pie graph"],
    }

    def __init__(self):
        """初始化图表分析器"""
        self._client = None

    def _get_client(self):
        """懒加载LLM客户端"""
        if self._client is None and CHART_ANALYSIS_ENABLED:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=DEEPSEEK_API_KEY,
                    base_url=DEEPSEEK_BASE_URL,
                )
            except Exception:
                pass
        return self._client

    def is_enabled(self) -> bool:
        """检查图表分析是否启用"""
        return CHART_ANALYSIS_ENABLED

    def detect_chart_type(self, ocr_text: str) -> str:
        """根据OCR文本推测图表类型

        Args:
            ocr_text: OCR提取的文本

        Returns:
            图表类型：bar/line/pie/unknown
        """
        text_lower = ocr_text.lower()
        for chart_type, keywords in self.CHART_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return chart_type
        return "unknown"

    def analyze(self, file_path: str, ocr_text: str = "") -> dict:
        """分析图表图片，返回结构化描述

        Args:
            file_path: 图片文件路径
            ocr_text: OCR已提取的文本

        Returns:
            字典包含：chart_type, title, data_points, trend, raw_description
        """
        if not self.is_enabled():
            return {"chart_type": "unknown", "title": "", "data_points": [], "trend": ""}

        # 先用关键词快速检测类型
        detected_type = self.detect_chart_type(ocr_text)

        # 调用LLM做详细分析
        llm_result = self._llm_analyze(file_path, ocr_text)

        if llm_result:
            llm_result["detected_type_hint"] = detected_type
            return llm_result

        # LLM失败时返回基础信息
        return {
            "chart_type": detected_type,
            "title": "",
            "data_points": [],
            "trend": "",
            "raw_description": ocr_text,
        }

    def _llm_analyze(self, file_path: str, ocr_text: str) -> dict | None:
        """调用LLM分析图表

        Args:
            file_path: 图片文件路径
            ocr_text: OCR文本

        Returns:
            结构化分析结果，失败返回None
        """
        client = self._get_client()
        if client is None:
            return None

        prompt = (
            "请分析这张图表图片，严格按以下JSON格式输出（不要输出其他内容）：\n"
            '{"chart_type": "柱状图/折线图/饼图/其他", '
            '"title": "图表标题", '
            '"data_points": ["数据点1描述", "数据点2描述"], '
            '"trend": "整体趋势或要点总结"}\n\n'
            f"OCR提取的文本：\n{ocr_text}\n"
            f"图片路径：{file_path}"
        )

        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()
            return self._parse_json_response(text)
        except Exception as e:
            print(f"图表LLM分析失败: {e}")
            return None

    def _parse_json_response(self, text: str) -> dict | None:
        """从LLM响应中解析JSON

        Args:
            text: LLM响应文本

        Returns:
            解析后的字典，失败返回None
        """
        import json
        import re

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 中的内容
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 部分
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def format_as_description(self, analysis: dict) -> str:
        """将分析结果格式化为可检索的自然语言描述

        Args:
            analysis: analyze()返回的字典

        Returns:
            自然语言描述文本
        """
        parts = []

        chart_type = analysis.get("chart_type", "未知类型")
        title = analysis.get("title", "")
        if title:
            parts.append(f"这是一张{chart_type}图表，标题为「{title}」。")
        else:
            parts.append(f"这是一张{chart_type}图表。")

        data_points = analysis.get("data_points", [])
        if data_points:
            parts.append("关键数据：")
            for dp in data_points:
                parts.append(f"- {dp}")

        trend = analysis.get("trend", "")
        if trend:
            parts.append(f"趋势总结：{trend}")

        return "\n".join(parts)
