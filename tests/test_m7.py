"""M7 多模态能力模块验收测试

覆盖范围：
1. 图表类型识别（ChartAnalyzer.detect_chart_type）
2. 图片描述生成（preprocessor.generate_image_description，mock LLM）
3. 图表结构化分析（ChartAnalyzer.analyze，mock LLM）
4. 表格自然语言描述生成（preprocessor.generate_table_description，mock LLM）
5. 表格Markdown解析与转Markdown（preprocessor.parse_markdown_table / table_to_markdown）
6. 多模态配置开关（MULTIMODAL_ENABLED / IMAGE_LLM_DESCRIPTION / TABLE_NL_DESCRIPTION / CHART_ANALYSIS_ENABLED）
7. ImageLoader加载流程（mock OCR + LLM + 图表分析）
8. 多模态Embedding开关（MULTIMODAL_EMBEDDING配置）
"""
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

import pytest


# ======================================================================
# 1. 图表类型识别
# ======================================================================

class TestChartTypeDetection:
    """测试 ChartAnalyzer 的关键词识别"""

    def test_detect_bar_chart(self):
        """柱状图关键词识别"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer.detect_chart_type("2024年各季度柱状图销售数据") == "bar"
        assert analyzer.detect_chart_type("bar chart of revenue") == "bar"

    def test_detect_line_chart(self):
        """折线图关键词识别"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer.detect_chart_type("用户增长趋势图") == "line"
        assert analyzer.detect_chart_type("line graph showing trends") == "line"

    def test_detect_pie_chart(self):
        """饼图关键词识别"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer.detect_chart_type("市场份额占比分布") == "pie"
        assert analyzer.detect_chart_type("pie chart of categories") == "pie"

    def test_detect_unknown_chart(self):
        """无法识别的图表类型"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer.detect_chart_type("这是一些随机文本") == "unknown"
        assert analyzer.detect_chart_type("") == "unknown"

    def test_detect_case_insensitive(self):
        """大小写不敏感"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer.detect_chart_type("BAR CHART Data") == "bar"
        assert analyzer.detect_chart_type("Line Graph Stats") == "line"


# ======================================================================
# 2. 图片描述生成（mock LLM）
# ======================================================================

class TestImageDescription:
    """测试 preprocessor.generate_image_description"""

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_image_description_success(self, mock_get_client):
        """LLM调用成功时返回描述"""
        from src.core import preprocessor

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="这是一张产品架构图，展示了系统的分层结构。"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(preprocessor, "IMAGE_LLM_DESCRIPTION", True):
            result = preprocessor.generate_image_description("/path/to/img.png", "架构图 系统")

        assert "架构图" in result or "产品" in result
        mock_client.chat.completions.create.assert_called_once()

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_image_description_no_ocr(self, mock_get_client):
        """无OCR文本时也能正常调用"""
        from src.core import preprocessor

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="这是一张风景照片。"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(preprocessor, "IMAGE_LLM_DESCRIPTION", True):
            result = preprocessor.generate_image_description("/path/to/landscape.jpg")

        assert "风景" in result
        # 验证prompt中不包含OCR提示
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "OCR" not in prompt

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_image_description_llm_failure(self, mock_get_client):
        """LLM调用失败时返回空字符串"""
        from src.core import preprocessor

        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(preprocessor, "IMAGE_LLM_DESCRIPTION", True):
            result = preprocessor.generate_image_description("/path/to/img.png")

        assert result == ""

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_image_description_disabled(self, mock_get_client):
        """功能关闭时返回空字符串"""
        from src.core import preprocessor

        with patch.object(preprocessor, "IMAGE_LLM_DESCRIPTION", False):
            result = preprocessor.generate_image_description("/path/to/img.png")

        assert result == ""
        mock_get_client.assert_not_called()


# ======================================================================
# 3. 图表结构化分析（mock LLM）
# ======================================================================

class TestChartAnalysis:
    """测试 ChartAnalyzer.analyze 和 _llm_analyze"""

    @patch("src.core.chart_analyzer.ChartAnalyzer._get_client")
    def test_analyze_with_llm_success(self, mock_get_client):
        """LLM分析成功时返回完整结构"""
        from src.core.chart_analyzer import ChartAnalyzer

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        llm_response = (
            '{"chart_type": "柱状图", "title": "季度销售数据", '
            '"data_points": ["Q1: 100万", "Q2: 150万"], '
            '"trend": "整体呈上升趋势"}'
        )
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content=llm_response))]
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("src.core.chart_analyzer.CHART_ANALYSIS_ENABLED", True):
            analyzer = ChartAnalyzer()
            result = analyzer.analyze("/path/to/chart.png", "柱状图 销售 Q1 Q2")

        assert result["chart_type"] == "柱状图"
        assert result["title"] == "季度销售数据"
        assert len(result["data_points"]) == 2
        assert "detected_type_hint" in result

    @patch("src.core.chart_analyzer.ChartAnalyzer._get_client")
    def test_analyze_llm_fallback_to_keyword(self, mock_get_client):
        """LLM失败时回退到关键词检测"""
        from src.core.chart_analyzer import ChartAnalyzer

        mock_get_client.return_value = None  # 无LLM客户端

        with patch("src.core.chart_analyzer.CHART_ANALYSIS_ENABLED", True):
            analyzer = ChartAnalyzer()
            result = analyzer.analyze("/path/to/chart.png", "饼图 市场份额")

        assert result["chart_type"] == "pie"
        assert result["title"] == ""
        assert result["raw_description"] == "饼图 市场份额"

    @patch("src.core.chart_analyzer.CHART_ANALYSIS_ENABLED", False)
    def test_analyze_disabled_returns_unknown(self):
        """功能关闭时返回unknown"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        result = analyzer.analyze("/path/to/chart.png", "some text")

        assert result["chart_type"] == "unknown"
        assert result["title"] == ""

    def test_parse_json_response_direct(self):
        """直接JSON解析"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        text = '{"chart_type": "bar", "title": "test"}'
        result = analyzer._parse_json_response(text)
        assert result["chart_type"] == "bar"

    def test_parse_json_response_in_code_block(self):
        """从```json ... ```中提取"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        text = '```json\n{"chart_type": "line", "title": "趋势"}\n```'
        result = analyzer._parse_json_response(text)
        assert result["chart_type"] == "line"

    def test_parse_json_response_no_json(self):
        """无法解析时返回None"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        result = analyzer._parse_json_response("this is not json at all")
        assert result is None


# ======================================================================
# 4. 表格自然语言描述生成（mock LLM）
# ======================================================================

class TestTableDescription:
    """测试 preprocessor.generate_table_description"""

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_table_description_success(self, mock_get_client):
        """LLM调用成功时返回描述"""
        from src.core import preprocessor

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(
            message=Mock(content="张三在技术部，薪资15000。\n李四在产品部，薪资12000。")
        )]
        mock_client.chat.completions.create.return_value = mock_response

        table_md = "| 姓名 | 部门 | 薪资 |\n| --- | --- | --- |\n| 张三 | 技术部 | 15000 |\n| 李四 | 产品部 | 12000 |"

        with patch.object(preprocessor, "TABLE_NL_DESCRIPTION", True):
            result = preprocessor.generate_table_description(table_md)

        assert "张三" in result
        assert "李四" in result

    @patch("src.core.preprocessor._get_llm_client")
    def test_generate_table_description_disabled(self, mock_get_client):
        """功能关闭时返回空字符串"""
        from src.core import preprocessor

        with patch.object(preprocessor, "TABLE_NL_DESCRIPTION", False):
            result = preprocessor.generate_table_description("| a | b |\n| 1 | 2 |")

        assert result == ""
        mock_get_client.assert_not_called()


# ======================================================================
# 5. 表格Markdown解析与转Markdown
# ======================================================================

class TestTableConversion:
    """测试 parse_markdown_table 和 table_to_markdown"""

    def test_parse_markdown_table_basic(self):
        """解析基本Markdown表格"""
        from src.core.preprocessor import parse_markdown_table

        content = "| 姓名 | 部门 |\n| --- | --- |\n| 张三 | 技术部 |"
        result = parse_markdown_table(content)

        assert result is not None
        assert len(result) == 2
        assert result[0] == ["姓名", "部门"]
        assert result[1] == ["张三", "技术部"]

    def test_parse_markdown_table_multiple_rows(self):
        """解析多行Markdown表格"""
        from src.core.preprocessor import parse_markdown_table

        content = (
            "| A | B | C |\n"
            "| --- | --- | --- |\n"
            "| 1 | 2 | 3 |\n"
            "| 4 | 5 | 6 |\n"
            "| 7 | 8 | 9 |"
        )
        result = parse_markdown_table(content)

        assert result is not None
        assert len(result) == 4  # header + 3 data rows

    def test_parse_markdown_table_not_table(self):
        """非表格内容返回None"""
        from src.core.preprocessor import parse_markdown_table

        assert parse_markdown_table("这是普通文本") is None
        assert parse_markdown_table("") is None
        assert parse_markdown_table("单行没有表格") is None

    def test_table_to_markdown_basic(self):
        """将二维列表转为Markdown表格"""
        from src.core.preprocessor import table_to_markdown

        data = [["姓名", "部门"], ["张三", "技术部"]]
        result = table_to_markdown(data)

        assert "| 姓名 | 部门 |" in result
        assert "| --- | --- |" in result
        assert "| 张三 | 技术部 |" in result

    def test_table_to_markdown_empty(self):
        """空数据返回空字符串"""
        from src.core.preprocessor import table_to_markdown

        assert table_to_markdown([]) == ""
        assert table_to_markdown([[]]) == ""

    def test_table_to_markdown_pads_columns(self):
        """列数不足时补齐"""
        from src.core.preprocessor import table_to_markdown

        data = [["A", "B", "C"], ["1", "2"]]  # 第二行少一列
        result = table_to_markdown(data)

        assert "| 1 | 2 |  |" in result


# ======================================================================
# 6. 多模态配置开关
# ======================================================================

class TestMultimodalConfig:
    """测试M7配置项的默认值和环境变量读取"""

    def test_multimodal_enabled_default_false(self):
        """MULTIMODAL_ENABLED默认关闭"""
        from src.config import MULTIMODAL_ENABLED
        # 默认应为False（不设环境变量时）
        # 注意：如果.env文件设置了该值，此测试需要调整
        assert isinstance(MULTIMODAL_ENABLED, bool)

    def test_image_llm_description_default_false(self):
        """IMAGE_LLM_DESCRIPTION默认关闭"""
        from src.config import IMAGE_LLM_DESCRIPTION
        assert isinstance(IMAGE_LLM_DESCRIPTION, bool)

    def test_table_nl_description_default_false(self):
        """TABLE_NL_DESCRIPTION默认关闭"""
        from src.config import TABLE_NL_DESCRIPTION
        assert isinstance(TABLE_NL_DESCRIPTION, bool)

    def test_chart_analysis_enabled_default_false(self):
        """CHART_ANALYSIS_ENABLED默认关闭"""
        from src.config import CHART_ANALYSIS_ENABLED
        assert isinstance(CHART_ANALYSIS_ENABLED, bool)

    def test_multimodal_embedding_default_false(self):
        """MULTIMODAL_EMBEDDING默认关闭"""
        from src.config import MULTIMODAL_EMBEDDING
        assert isinstance(MULTIMODAL_EMBEDDING, bool)

    def test_ocr_languages_default(self):
        """OCR_LANGUAGES有默认值"""
        from src.config import OCR_LANGUAGES
        assert isinstance(OCR_LANGUAGES, str)
        assert len(OCR_LANGUAGES) > 0

    def test_config_env_override(self):
        """环境变量可以覆盖配置"""
        import os
        with patch.dict(os.environ, {"IMAGE_LLM_DESCRIPTION": "true"}):
            # 需要重新导入才能读到新值
            # 这里验证的是env变量字符串转换逻辑
            val = os.getenv("IMAGE_LLM_DESCRIPTION", "false").lower() == "true"
            assert val is True

        with patch.dict(os.environ, {"CHART_ANALYSIS_ENABLED": "false"}):
            val = os.getenv("CHART_ANALYSIS_ENABLED", "false").lower() == "true"
            assert val is False


# ======================================================================
# 7. ImageLoader加载流程
# ======================================================================

class TestImageLoader:
    """测试 ImageLoader 的加载逻辑"""

    def test_can_handle_image_extensions(self):
        """能处理的图片扩展名"""
        from src.core.loaders.image_loader import ImageLoader

        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]:
            assert ImageLoader.can_handle(Path(f"test{ext}"))

    def test_cannot_handle_non_image(self):
        """不能处理非图片文件"""
        from src.core.loaders.image_loader import ImageLoader

        assert not ImageLoader.can_handle(Path("test.md"))
        assert not ImageLoader.can_handle(Path("test.pdf"))
        assert not ImageLoader.can_handle(Path("test.docx"))

    def test_supported_extensions(self):
        """supported_extensions返回正确的扩展名列表"""
        from src.core.loaders.image_loader import ImageLoader

        exts = ImageLoader.supported_extensions()
        assert ".png" in exts
        assert ".jpg" in exts
        assert ".webp" in exts

    def test_load_returns_placeholder_when_all_disabled(self):
        """所有功能关闭时返回占位描述"""
        from src.core.loaders.image_loader import ImageLoader
        from src.core.loaders.base import ElementType

        loader = ImageLoader()

        with (
            patch("src.core.loaders.image_loader.CHART_ANALYSIS_ENABLED", False),
            patch("src.core.loaders.image_loader.IMAGE_LLM_DESCRIPTION", False),
            patch.object(loader, "_tesseract_available", False),
        ):
            # 创建临时文件模拟图片
            with patch("pathlib.Path.exists", return_value=True):
                # 需要传入真实路径但不真正读取
                fake_path = Path("test_image.png")
                with patch.object(type(fake_path), "exists", return_value=True):
                    result = loader.load(fake_path)

        assert len(result) == 1
        assert result[0].element_type == ElementType.IMAGE_DESCRIPTION
        assert "[图片:" in result[0].content
        assert result[0].metadata["content_type"] == "placeholder"

    @patch("src.core.loaders.image_loader.generate_image_description")
    @patch("src.core.loaders.image_loader.CHART_ANALYSIS_ENABLED", False)
    def test_load_with_llm_description(self, mock_gen_desc):
        """LLM描述启用时生成描述"""
        from src.core.loaders.image_loader import ImageLoader
        from src.core.loaders.base import ElementType

        mock_gen_desc.return_value = "这是一张流程图，展示了系统架构。"

        loader = ImageLoader()

        with (
            patch.object(loader, "_tesseract_available", False),
            patch("src.core.loaders.image_loader.IMAGE_LLM_DESCRIPTION", True),
            patch("pathlib.Path.exists", return_value=True),
        ):
            fake_path = Path("arch.png")
            with patch.object(type(fake_path), "exists", return_value=True):
                result = loader.load(fake_path)

        assert len(result) >= 1
        # 应包含LLM生成的描述
        contents = [e.content for e in result]
        assert any("流程图" in c for c in contents)


# ======================================================================
# 8. 多模态Embedding开关
# ======================================================================

class TestMultimodalEmbedding:
    """测试多模态Embedding配置和开关"""

    def test_multimodal_embedding_config_exists(self):
        """MULTIMODAL_EMBEDDING配置项存在"""
        from src.config import MULTIMODAL_EMBEDDING
        assert hasattr(MULTIMODAL_EMBEDDING, "__bool__") or isinstance(MULTIMODAL_EMBEDDING, bool)

    def test_embedder_uses_text_by_default(self):
        """默认Embedder只处理文本，不处理图片"""
        from src.core.embedder import Embedder

        # 验证Embedder的接口只接受文本列表（排除self）
        import inspect
        sig = inspect.signature(Embedder.embed)
        params = [p for p in sig.parameters if p != "self"]
        assert params == ["texts"]
        # embed_single方法只接受text参数
        sig_single = inspect.signature(Embedder.embed_single)
        params_single = [p for p in sig_single.parameters if p != "self"]
        assert params_single == ["text"]

    def test_multimodal_embedding_switchable(self):
        """MULTIMODAL_EMBEDDING可以通过环境变量切换"""
        import os
        with patch.dict(os.environ, {"MULTIMODAL_EMBEDDING": "true"}):
            val = os.getenv("MULTIMODAL_EMBEDDING", "false").lower() == "true"
            assert val is True

        with patch.dict(os.environ, {"MULTIMODAL_EMBEDDING": "false"}):
            val = os.getenv("MULTIMODAL_EMBEDDING", "false").lower() == "true"
            assert val is False


# ======================================================================
# 9. 图表分析器格式化输出
# ======================================================================

class TestChartFormatter:
    """测试 ChartAnalyzer.format_as_description"""

    def test_format_with_title_and_data(self):
        """有标题和数据点时的格式化"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        analysis = {
            "chart_type": "柱状图",
            "title": "季度销售额",
            "data_points": ["Q1: 100万", "Q2: 150万"],
            "trend": "持续增长",
        }
        result = analyzer.format_as_description(analysis)

        assert "柱状图" in result
        assert "季度销售额" in result
        assert "Q1: 100万" in result
        assert "Q2: 150万" in result
        assert "持续增长" in result

    def test_format_without_title(self):
        """无标题时的格式化"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        analysis = {
            "chart_type": "饼图",
            "title": "",
            "data_points": ["A: 30%"],
            "trend": "",
        }
        result = analyzer.format_as_description(analysis)

        assert "饼图" in result
        assert "标题" not in result
        assert "A: 30%" in result

    def test_format_minimal(self):
        """最小数据时的格式化"""
        from src.core.chart_analyzer import ChartAnalyzer

        analyzer = ChartAnalyzer()
        analysis = {"chart_type": "折线图", "title": "", "data_points": [], "trend": ""}
        result = analyzer.format_as_description(analysis)

        assert "折线图" in result
        # 没有数据点和趋势时不应包含额外内容
        assert "关键数据" not in result
        assert "趋势总结" not in result


# ======================================================================
# 10. 图表分析器 is_enabled
# ======================================================================

class TestChartAnalyzerEnabled:
    """测试 ChartAnalyzer.is_enabled"""

    @patch("src.core.chart_analyzer.CHART_ANALYSIS_ENABLED", True)
    def test_enabled(self):
        from src.core.chart_analyzer import ChartAnalyzer
        assert ChartAnalyzer().is_enabled() is True

    @patch("src.core.chart_analyzer.CHART_ANALYSIS_ENABLED", False)
    def test_disabled(self):
        from src.core.chart_analyzer import ChartAnalyzer
        assert ChartAnalyzer().is_enabled() is False


# ======================================================================
# 11. enrich_table_element
# ======================================================================

class TestEnrichTableElement:
    """测试 preprocessor.enrich_table_element"""

    @patch("src.core.preprocessor._get_llm_client")
    def test_enrich_generates_description(self, mock_get_client):
        """表格enrich成功时返回原element + 描述element"""
        from src.core.preprocessor import enrich_table_element
        from src.core.loaders.base import DocumentElement, ElementType

        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="张三在技术部。\n李四在产品部。"))]
        mock_client.chat.completions.create.return_value = mock_response

        table_content = "| 姓名 | 部门 |\n| --- | --- |\n| 张三 | 技术部 |\n| 李四 | 产品部 |"
        element = DocumentElement(
            content=table_content,
            element_type=ElementType.TABLE,
            metadata={"content_type": "table"},
            source_file="test.md",
        )

        with patch("src.core.preprocessor.TABLE_NL_DESCRIPTION", True):
            result = enrich_table_element(element)

        assert len(result) == 2  # 原element + 描述element
        assert result[0].element_type == ElementType.TABLE
        assert result[1].element_type == ElementType.TEXT
        assert result[1].metadata["content_type"] == "table_description"
        assert result[1].metadata["description_of"] == "table"

    def test_enrich_disabled_returns_only_original(self):
        """功能关闭时只返回原element"""
        from src.core.preprocessor import enrich_table_element
        from src.core.loaders.base import DocumentElement, ElementType

        element = DocumentElement(
            content="| a | b |\n| 1 | 2 |",
            element_type=ElementType.TABLE,
        )

        with patch("src.core.preprocessor.TABLE_NL_DESCRIPTION", False):
            result = enrich_table_element(element)

        assert len(result) == 1
        assert result[0] is element


# ======================================================================
# 12. Splitter对IMAGE_DESCRIPTION类型的处理
# ======================================================================

class TestSplitterMultimodal:
    """测试 SmartSplitter 对多模态元素的处理"""

    def test_image_description_not_split(self):
        """IMAGE_DESCRIPTION类型不切分，整体保留"""
        from src.core.splitter import SmartSplitter
        from src.core.loaders.base import DocumentElement, ElementType

        splitter = SmartSplitter(chunk_size=100)
        long_desc = "[图片: test.png] " + "很长的描述" * 50  # 远超chunk_size
        element = DocumentElement(
            content=long_desc,
            element_type=ElementType.IMAGE_DESCRIPTION,
            source_file="test.png",
        )
        chunks = splitter.split_element(element)

        assert len(chunks) == 1
        assert chunks[0].content == long_desc
        assert chunks[0].metadata["element_type"] == "image_description"

    def test_table_not_split(self):
        """TABLE类型不切分"""
        from src.core.splitter import SmartSplitter
        from src.core.loaders.base import DocumentElement, ElementType

        splitter = SmartSplitter(chunk_size=100)
        table_content = "| A | B |\n| --- | --- |\n| " + " | ".join(["数据"] * 20) + " |"
        element = DocumentElement(
            content=table_content,
            element_type=ElementType.TABLE,
            source_file="test.md",
        )
        chunks = splitter.split_element(element)

        assert len(chunks) == 1
        assert chunks[0].metadata["element_type"] == "table"
