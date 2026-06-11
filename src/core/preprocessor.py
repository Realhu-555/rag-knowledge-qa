"""预处理器：表格结构化描述、图片描述生成"""
import re
from typing import Any

from src.config import (
    TABLE_NL_DESCRIPTION,
    IMAGE_LLM_DESCRIPTION,
    CHART_ANALYSIS_ENABLED,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)


def _get_llm_client():
    """获取LLM客户端（懒加载）"""
    try:
        from openai import OpenAI
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    except Exception:
        return None


def _call_llm(prompt: str, max_tokens: int = 500) -> str:
    """调用LLM生成文本

    Args:
        prompt: 提示词
        max_tokens: 最大token数

    Returns:
        LLM生成的文本，失败返回空字符串
    """
    client = _get_llm_client()
    if client is None:
        return ""
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return ""


def table_to_markdown(table_data: list[list[str]]) -> str:
    """将二维列表转为Markdown表格

    Args:
        table_data: 二维列表，第一行为表头

    Returns:
        Markdown格式的表格字符串
    """
    if not table_data or not table_data[0]:
        return ""

    lines = []
    header = table_data[0]
    lines.append("| " + " | ".join(str(c) for c in header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in table_data[1:]:
        # 补齐列数
        padded = list(row) + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(str(c) for c in padded[:len(header)]) + " |")
    return "\n".join(lines)


def parse_markdown_table(content: str) -> list[list[str]] | None:
    """解析Markdown表格为二维列表

    Args:
        content: Markdown表格文本

    Returns:
        二维列表，或None（不是表格）
    """
    lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return None

    rows = []
    for line in lines:
        if not line.startswith("|"):
            return None
        cells = [c.strip() for c in line.split("|")]
        # split("|") 两端会产生空字符串，去掉
        cells = [c for c in cells if c != ""]
        # 跳过分隔行 "---"
        if all(re.match(r'^-+$', c) for c in cells):
            continue
        rows.append(cells)

    return rows if len(rows) >= 2 else None


def generate_table_description(table_md: str) -> str:
    """用LLM将Markdown表格转为自然语言描述

    Args:
        table_md: Markdown格式的表格

    Returns:
        自然语言描述，失败时返回空字符串
    """
    if not TABLE_NL_DESCRIPTION:
        return ""

    prompt = (
        "请将以下表格转换为自然语言描述。要求：\n"
        "1. 每一行数据生成一句独立的描述\n"
        "2. 描述要包含关键字段名和值\n"
        "3. 格式如：\"张三在技术部，薪资15000\"\n"
        "4. 不要添加额外解释，只输出描述\n\n"
        f"表格：\n{table_md}"
    )
    return _call_llm(prompt, max_tokens=800)


def generate_image_description(file_path: str, ocr_text: str = "") -> str:
    """用LLM生成图片描述

    Args:
        file_path: 图片文件路径
        ocr_text: OCR已提取的文本（可选）

    Returns:
        图片描述文本
    """
    if not IMAGE_LLM_DESCRIPTION:
        return ""

    ocr_hint = f"\nOCR提取的文本：{ocr_text}" if ocr_text else ""
    prompt = (
        "请描述这张图片的内容。要求：\n"
        "1. 简要描述图片的主题和内容\n"
        "2. 如果是图表，描述图表类型和关键数据\n"
        "3. 如果包含文字，整合到描述中\n"
        "4. 用中文回答，200字以内\n"
        f"{ocr_hint}\n"
        f"图片文件：{file_path}"
    )
    return _call_llm(prompt, max_tokens=300)


def generate_chart_description(file_path: str, ocr_text: str = "") -> str:
    """用LLM分析图表并生成结构化描述

    Args:
        file_path: 图片文件路径
        ocr_text: OCR已提取的文本

    Returns:
        图表结构化描述
    """
    if not CHART_ANALYSIS_ENABLED:
        return ""

    prompt = (
        "请分析这张图表图片，生成结构化描述。要求：\n"
        "1. 判断图表类型（柱状图/折线图/饼图/其他）\n"
        "2. 提取关键数据点和趋势\n"
        "3. 用JSON格式输出：\n"
        '   {"chart_type": "类型", "title": "标题", "data_points": ["数据点1", "数据点2"], "trend": "趋势描述"}\n'
        f"OCR提取的文本：{ocr_text}\n"
        f"图片文件：{file_path}"
    )
    return _call_llm(prompt, max_tokens=500)


def enrich_table_element(element: Any) -> list[Any]:
    """为表格元素生成自然语言描述

    Args:
        element: DocumentElement，element_type=table

    Returns:
        [原element, 描述element] 的列表；未启用或失败则只返回原element
    """
    from src.core.loaders.base import DocumentElement, ElementType

    result = [element]

    if not TABLE_NL_DESCRIPTION:
        return result

    table_data = parse_markdown_table(element.content)
    if table_data is None:
        return result

    desc = generate_table_description(element.content)
    if not desc:
        return result

    desc_metadata = {
        **element.metadata,
        "content_type": "table_description",
        "description_of": "table",
    }
    desc_element = DocumentElement(
        content=desc,
        element_type=ElementType.TEXT,
        metadata=desc_metadata,
        source_file=element.source_file,
        page_number=element.page_number,
    )
    result.append(desc_element)
    return result
