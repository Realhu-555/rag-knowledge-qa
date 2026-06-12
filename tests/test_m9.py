"""M9 回答质量自动评测模块验收测试

覆盖范围：
1. 评测集格式验证（30个用例，字段完整）
2. 语义相似度计算（余弦相似度）
3. 评测报告生成（Markdown格式）
4. evaluations表存储（SQLite读写）
5. 告警触发（准确率下降>5%）
6. 评测汇总计算
7. 关键词评分
8. M9配置项默认值
"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Mock掉sentence_transformers和torch，避免torch循环导入问题
_mock_st = MagicMock()
_mock_torch = MagicMock()
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = _mock_st
if "torch" not in sys.modules:
    sys.modules["torch"] = _mock_torch

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


# ======================================================================
# 1. 评测集格式验证
# ======================================================================

class TestEvalDatasetFormat:
    """测试评测集文件格式"""

    def test_load_test_cases(self):
        """能正确加载评测集JSON文件"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        assert isinstance(cases, list)
        assert len(cases) == 30

    def test_all_cases_have_required_fields(self):
        """每个用例都包含必要字段"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        required_fields = {"id", "question", "expected_keywords", "expected_answer", "source_files", "category"}

        for case in cases:
            missing = required_fields - set(case.keys())
            assert not missing, f"用例 {case.get('id', '?')} 缺少字段: {missing}"

    def test_case_ids_are_unique(self):
        """用例ID不重复"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), "存在重复的用例ID"

    def test_case_ids_are_sequential(self):
        """用例ID从001到030连续编号"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        ids = [c["id"] for c in cases]
        expected = [f"{i:03d}" for i in range(1, 31)]
        assert ids == expected

    def test_categories_are_valid(self):
        """所有category都是合法值"""
        from evaluate import load_test_cases

        valid_categories = {"simple_fact", "multi_doc", "out_of_scope", "vague"}
        cases = load_test_cases()
        for case in cases:
            assert case["category"] in valid_categories, \
                f"用例 {case['id']} 的category '{case['category']}' 不合法"

    def test_expected_keywords_are_lists(self):
        """expected_keywords都是列表"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        for case in cases:
            assert isinstance(case["expected_keywords"], list), \
                f"用例 {case['id']} 的expected_keywords不是列表"

    def test_category_distribution(self):
        """类别分布合理：有simple_fact、multi_doc、out_of_scope、vague"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        categories = {}
        for c in cases:
            cat = c["category"]
            categories[cat] = categories.get(cat, 0) + 1

        assert "simple_fact" in categories
        assert "multi_doc" in categories
        assert "out_of_scope" in categories
        assert "vague" in categories

    def test_out_of_scope_have_empty_source_files(self):
        """out_of_scope用例的source_files为空列表"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        out_of_scope = [c for c in cases if c["category"] == "out_of_scope"]
        for case in out_of_scope:
            assert case["source_files"] == [], \
                f"用例 {case['id']} 是out_of_scope但source_files不为空"

    def test_non_out_of_scope_have_source_files(self):
        """非out_of_scope用例应有source_files"""
        from evaluate import load_test_cases

        cases = load_test_cases()
        in_scope = [c for c in cases if c["category"] != "out_of_scope"]
        for case in in_scope:
            assert len(case["source_files"]) > 0, \
                f"用例 {case['id']} 非out_of_scope但source_files为空"


# ======================================================================
# 2. 语义相似度计算
# ======================================================================

class TestCosineSimilarity:
    """测试余弦相似度计算"""

    def test_identical_vectors(self):
        """相同向量相似度为1.0"""
        from evaluate import _cosine_similarity

        vec = [1.0, 2.0, 3.0, 4.0]
        result = _cosine_similarity(vec, vec)
        assert abs(result - 1.0) < 1e-6

    def test_opposite_vectors(self):
        """反向向量相似度为-1.0"""
        from evaluate import _cosine_similarity

        vec_a = [1.0, 2.0, 3.0]
        vec_b = [-1.0, -2.0, -3.0]
        result = _cosine_similarity(vec_a, vec_b)
        assert abs(result - (-1.0)) < 1e-6

    def test_orthogonal_vectors(self):
        """正交向量相似度为0.0"""
        from evaluate import _cosine_similarity

        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        result = _cosine_similarity(vec_a, vec_b)
        assert abs(result) < 1e-6

    def test_zero_vector_returns_zero(self):
        """零向量返回0.0"""
        from evaluate import _cosine_similarity

        result = _cosine_similarity([0.0, 0.0], [1.0, 2.0])
        assert result == 0.0

    def test_both_zero_vectors(self):
        """两个零向量返回0.0"""
        from evaluate import _cosine_similarity

        result = _cosine_similarity([0.0, 0.0], [0.0, 0.0])
        assert result == 0.0

    def test_partial_similarity(self):
        """部分相似的向量返回中间值"""
        from evaluate import _cosine_similarity

        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.7, 0.7, 0.0]
        result = _cosine_similarity(vec_a, vec_b)
        assert 0.0 < result < 1.0
        # 预期 cos(45度) ≈ 0.7071
        assert abs(result - 0.7071) < 0.01

    def test_compute_semantic_similarity_with_mock_embedder(self):
        """compute_semantic_similarity用mock embedder正确调用"""
        from evaluate import compute_semantic_similarity

        mock_embedder = Mock()
        mock_embedder.embed.return_value = [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ]

        result = compute_semantic_similarity("hello", "hello", mock_embedder)
        assert abs(result - 1.0) < 1e-6
        mock_embedder.embed.assert_called_once_with(["hello", "hello"])

    def test_compute_semantic_similarity_empty_answer(self):
        """空答案返回0.0"""
        from evaluate import compute_semantic_similarity

        mock_embedder = Mock()
        assert compute_semantic_similarity("", "expected", mock_embedder) == 0.0
        assert compute_semantic_similarity("answer", "", mock_embedder) == 0.0
        assert compute_semantic_similarity("", "", mock_embedder) == 0.0


# ======================================================================
# 3. 评测报告生成
# ======================================================================

class TestWriteReport:
    """测试Markdown评测报告生成"""

    def test_write_report_creates_file(self):
        """报告文件被正确创建"""
        from evaluate import write_report

        summary = {
            "version": "test_v1",
            "total_cases": 10,
            "success_cases": 8,
            "retrieval_hit_rate": 0.9,
            "answer_accuracy": 0.75,
            "citation_accuracy": 0.875,
            "avg_semantic_similarity": 0.82,
            "avg_latency_ms": 1200.0,
            "category_accuracy": {"simple_fact": 0.8, "multi_doc": 0.7},
            "results": [
                {
                    "case_id": "001",
                    "question": "测试问题",
                    "accuracy": 0.8,
                    "semantic_similarity": 0.9,
                    "retrieval_hit": True,
                    "citation_correct": True,
                    "elapsed_ms": 100,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    report_path = write_report(summary)

                    assert Path(report_path).exists()
                    content = Path(report_path).read_text(encoding="utf-8")

                    # 验证报告包含关键内容
                    assert "# RAG 智能问答系统评测报告" in content
                    assert "test_v1" in content
                    assert "10" in content  # total_cases
                    assert "90.0%" in content  # retrieval_hit_rate (0.9)
                    assert "75.0%" in content  # answer_accuracy (0.75)
                    assert "87.5%" in content  # citation_accuracy
                    assert "0.820" in content  # avg_semantic_similarity
                    assert "1200" in content  # avg_latency_ms

    def test_write_report_with_comparison(self):
        """报告包含版本对比数据"""
        from evaluate import write_report

        summary = {
            "version": "test_v2",
            "total_cases": 10,
            "success_cases": 10,
            "retrieval_hit_rate": 0.95,
            "answer_accuracy": 0.85,
            "citation_accuracy": 0.9,
            "avg_semantic_similarity": 0.88,
            "avg_latency_ms": 1000.0,
            "category_accuracy": {},
            "comparison": {
                "prev_answer_accuracy": 0.80,
                "curr_answer_accuracy": 0.85,
                "prev_retrieval_hit_rate": 0.90,
                "curr_retrieval_hit_rate": 0.95,
                "prev_citation_accuracy": 0.85,
                "curr_citation_accuracy": 0.90,
                "prev_avg_semantic_similarity": 0.85,
                "curr_avg_semantic_similarity": 0.88,
            },
            "results": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    report_path = write_report(summary)
                    content = Path(report_path).read_text(encoding="utf-8")

                    assert "与上次评测对比" in content
                    assert "回答准确率" in content

    def test_write_report_empty_results(self):
        """空结果列表也能生成报告"""
        from evaluate import write_report

        summary = {
            "version": "empty_v1",
            "total_cases": 0,
            "success_cases": 0,
            "retrieval_hit_rate": 0.0,
            "answer_accuracy": 0.0,
            "citation_accuracy": 0.0,
            "avg_semantic_similarity": 0.0,
            "avg_latency_ms": 0.0,
            "category_accuracy": {},
            "results": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    report_path = write_report(summary)
                    assert Path(report_path).exists()


# ======================================================================
# 4. evaluations表存储
# ======================================================================

class TestEvaluationDatabase:
    """测试SQLite evaluations表的读写"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """每个测试用例使用独立的临时数据库"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_rag.db"

        with patch("src.storage.database.DB_PATH", self.db_path):
            from src.storage.database import init_db
            init_db()
            yield

        self.tmpdir.cleanup()

    def test_save_and_list_evaluation(self):
        """保存评测结果并查询"""
        with patch("src.storage.database.DB_PATH", self.db_path):
            from src.storage.database import save_evaluation, list_evaluations

            eval_id = save_evaluation(
                version="v1",
                total_cases=30,
                success_cases=28,
                retrieval_hit_rate=0.93,
                answer_accuracy=0.85,
                citation_accuracy=0.9,
                avg_semantic_similarity=0.82,
                avg_latency_ms=1200.0,
                details='{"key": "value"}',
            )

            assert eval_id is not None

            evals = list_evaluations()
            assert len(evals) >= 1
            latest = evals[0]
            assert latest["version"] == "v1"
            assert latest["total_cases"] == 30
            assert latest["answer_accuracy"] == 0.85

    def test_get_latest_evaluation(self):
        """获取最新评测记录"""
        with patch("src.storage.database.DB_PATH", self.db_path):
            from src.storage.database import save_evaluation, get_latest_evaluation

            save_evaluation("v1", 30, 28, 0.93, 0.80, 0.85, 0.82, 1200.0)
            save_evaluation("v2", 30, 29, 0.97, 0.88, 0.92, 0.86, 1100.0)

            latest = get_latest_evaluation()
            assert latest is not None
            assert latest["version"] == "v2"
            assert latest["answer_accuracy"] == 0.88

    def test_get_previous_evaluation(self):
        """获取上一次评测记录"""
        with patch("src.storage.database.DB_PATH", self.db_path):
            from src.storage.database import (
                save_evaluation,
                get_previous_evaluation,
            )

            save_evaluation("v1", 30, 28, 0.93, 0.80, 0.85, 0.82, 1200.0)
            save_evaluation("v2", 30, 29, 0.97, 0.88, 0.92, 0.86, 1100.0)

            prev = get_previous_evaluation()
            assert prev is not None
            assert prev["version"] == "v1"
            assert prev["answer_accuracy"] == 0.80

    def test_get_previous_evaluation_none_when_single(self):
        """只有一条记录时get_previous_evaluation返回None"""
        with patch("src.storage.database.DB_PATH", self.db_path):
            from src.storage.database import (
                save_evaluation,
                get_previous_evaluation,
            )

            save_evaluation("v1", 30, 28, 0.93, 0.80, 0.85, 0.82, 1200.0)
            prev = get_previous_evaluation()
            assert prev is None

    def test_evaluations_table_has_all_columns(self):
        """evaluations表包含所有必需列"""
        with patch("src.storage.database.DB_PATH", self.db_path):
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("PRAGMA table_info(evaluations)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            expected_columns = {
                "id", "version", "total_cases", "success_cases",
                "retrieval_hit_rate", "answer_accuracy", "citation_accuracy",
                "avg_semantic_similarity", "avg_latency_ms", "details", "created_at",
            }
            assert expected_columns.issubset(columns)


# ======================================================================
# 5. 告警触发
# ======================================================================

class TestQualityAlert:
    """测试准确率下降告警机制"""

    def test_alert_triggered_when_drop_exceeds_threshold(self):
        """准确率下降超过阈值时触发告警"""
        from src.core.eval_scheduler import _check_quality_alert

        prev_eval = {"answer_accuracy": 0.90}

        with patch("src.core.eval_scheduler.logger") as mock_logger, \
             patch("src.core.eval_scheduler.EVAL_ALERT_DROP_THRESHOLD", 0.05), \
             patch("src.storage.database.get_previous_evaluation", return_value=prev_eval):
            current_summary = {"answer_accuracy": 0.80}
            _check_quality_alert(current_summary)
            # 应该触发告警
            warning_calls = [str(args) for args in mock_logger.warning.call_args_list]
            assert any("告警" in call for call in warning_calls), \
                f"未检测到告警日志，实际调用: {warning_calls}"

    def test_no_alert_when_drop_within_threshold(self):
        """准确率下降未超过阈值时不告警"""
        from src.core.eval_scheduler import _check_quality_alert

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "alert_test.db"
            with patch("src.storage.database.DB_PATH", db_path):
                from src.storage.database import init_db, save_evaluation
                init_db()
                # 保存历史记录
                save_evaluation("old", 30, 30, 1.0, 0.88, 1.0, 0.95, 500.0)
                # 当前准确率略降（在阈值内）
                current_summary = {"answer_accuracy": 0.85}

                with patch("src.core.eval_scheduler.logger") as mock_logger, \
                     patch("src.core.eval_scheduler.EVAL_ALERT_DROP_THRESHOLD", 0.05):
                    _check_quality_alert(current_summary)
                    # 不应该触发告警warning
                    warning_calls = mock_logger.warning.call_args_list
                    assert len(warning_calls) == 0, \
                        f"不应触发告警，但收到了: {warning_calls}"

    def test_no_alert_when_accuracy_improves(self):
        """准确率提升时不告警"""
        from src.core.eval_scheduler import _check_quality_alert

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "alert_test.db"
            with patch("src.storage.database.DB_PATH", db_path):
                from src.storage.database import init_db, save_evaluation
                init_db()
                save_evaluation("old", 30, 30, 1.0, 0.75, 1.0, 0.80, 500.0)
                current_summary = {"answer_accuracy": 0.85}

                with patch("src.core.eval_scheduler.logger") as mock_logger, \
                     patch("src.core.eval_scheduler.EVAL_ALERT_DROP_THRESHOLD", 0.05):
                    _check_quality_alert(current_summary)
                    mock_logger.warning.assert_not_called()

    def test_no_alert_first_evaluation(self):
        """首次评测无历史数据时不告警"""
        from src.core.eval_scheduler import _check_quality_alert

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "alert_test.db"
            with patch("src.storage.database.DB_PATH", db_path):
                from src.storage.database import init_db
                init_db()

                current_summary = {"answer_accuracy": 0.50}

                with patch("src.core.eval_scheduler.logger") as mock_logger:
                    _check_quality_alert(current_summary)
                    # 首次评测应记录info
                    info_calls = [str(args) for args in mock_logger.info.call_args_list]
                    assert any("首次评测" in call for call in info_calls)

    def test_alert_threshold_config(self):
        """EVAL_ALERT_DROP_THRESHOLD配置正确"""
        from src.config import EVAL_ALERT_DROP_THRESHOLD
        assert EVAL_ALERT_DROP_THRESHOLD == 0.05


# ======================================================================
# 6. 评测汇总计算
# ======================================================================

class TestComputeSummary:
    """测试评测汇总指标计算"""

    def test_summary_all_success(self):
        """全部成功时的汇总计算"""
        from evaluate import compute_summary

        results = [
            {
                "status": "success",
                "accuracy": 0.8,
                "semantic_similarity": 0.85,
                "elapsed_ms": 1000,
                "retrieval_hit": True,
                "citation_correct": True,
                "category": "simple_fact",
            },
            {
                "status": "success",
                "accuracy": 0.7,
                "semantic_similarity": 0.75,
                "elapsed_ms": 1200,
                "retrieval_hit": True,
                "citation_correct": False,
                "category": "simple_fact",
            },
            {
                "status": "success",
                "accuracy": 0.9,
                "semantic_similarity": 0.9,
                "elapsed_ms": 800,
                "retrieval_hit": True,
                "citation_correct": True,
                "category": "multi_doc",
            },
        ]

        summary = compute_summary(results, "test_v1")

        assert summary["version"] == "test_v1"
        assert summary["total_cases"] == 3
        assert summary["success_cases"] == 3
        assert abs(summary["answer_accuracy"] - 0.8) < 0.01  # (0.8+0.7+0.9)/3
        assert abs(summary["avg_semantic_similarity"] - 0.8333) < 0.01
        assert abs(summary["avg_latency_ms"] - 1000.0) < 0.01
        assert summary["retrieval_hit_rate"] == 1.0  # 3/3
        assert abs(summary["citation_accuracy"] - 0.6667) < 0.01  # 2/3

    def test_summary_with_errors(self):
        """包含错误用例时的汇总计算"""
        from evaluate import compute_summary

        results = [
            {
                "status": "success",
                "accuracy": 0.8,
                "semantic_similarity": 0.85,
                "elapsed_ms": 1000,
                "retrieval_hit": True,
                "citation_correct": True,
                "category": "simple_fact",
            },
            {
                "status": "error",
                "accuracy": 0.0,
                "semantic_similarity": 0.0,
                "elapsed_ms": 500,
                "retrieval_hit": False,
                "citation_correct": False,
                "category": "simple_fact",
            },
        ]

        summary = compute_summary(results, "test_errors")

        assert summary["total_cases"] == 2
        assert summary["success_cases"] == 1
        # 只计算成功的
        assert summary["answer_accuracy"] == 0.8
        assert summary["retrieval_hit_rate"] == 1.0

    def test_summary_all_errors(self):
        """全部错误时返回零值"""
        from evaluate import compute_summary

        results = [
            {
                "status": "error",
                "accuracy": 0.0,
                "semantic_similarity": 0.0,
                "elapsed_ms": 500,
                "retrieval_hit": False,
                "citation_correct": False,
                "category": "simple_fact",
            },
        ]

        summary = compute_summary(results, "test_all_error")

        assert summary["success_cases"] == 0
        assert summary["answer_accuracy"] == 0.0
        assert summary["avg_semantic_similarity"] == 0.0

    def test_summary_category_accuracy(self):
        """按类别准确率正确计算"""
        from evaluate import compute_summary

        results = [
            {
                "status": "success",
                "accuracy": 0.8,
                "semantic_similarity": 0.85,
                "elapsed_ms": 1000,
                "retrieval_hit": True,
                "citation_correct": True,
                "category": "simple_fact",
            },
            {
                "status": "success",
                "accuracy": 0.6,
                "semantic_similarity": 0.7,
                "elapsed_ms": 1000,
                "retrieval_hit": False,
                "citation_correct": False,
                "category": "multi_doc",
            },
        ]

        summary = compute_summary(results, "test_cat")

        assert summary["category_accuracy"]["simple_fact"] == 0.8
        assert summary["category_accuracy"]["multi_doc"] == 0.6


# ======================================================================
# 7. 关键词评分
# ======================================================================

class TestEvaluateAnswer:
    """测试基于关键词的回答评估"""

    def test_perfect_keyword_match(self):
        """所有关键词都匹配"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "RAG是检索增强生成技术，用于增强大模型的回答。",
            ["检索", "增强", "生成"],
        )
        assert result["keyword_score"] == 1.0
        assert result["hits"] == 3
        assert result["total_keywords"] == 3

    def test_partial_keyword_match(self):
        """部分关键词匹配"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "RAG是检索增强技术。",
            ["检索", "增强", "生成"],
        )
        assert result["keyword_score"] == pytest.approx(0.67, abs=0.01)
        assert result["hits"] == 2

    def test_no_keyword_match(self):
        """没有关键词匹配"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "今天天气不错。",
            ["检索", "增强", "生成"],
        )
        assert result["keyword_score"] == 0.0
        assert result["hits"] == 0

    def test_empty_keywords(self):
        """关键词列表为空"""
        from evaluate import evaluate_answer

        result = evaluate_answer("随便回答", [])
        assert result["keyword_score"] == 0.0
        assert result["total_keywords"] == 0

    def test_citation_detected(self):
        """检测到引用标注"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "根据[1]和[2]，RAG技术很有效。",
            ["RAG"],
        )
        assert result["citation_score"] == 1.0

    def test_no_citation(self):
        """未检测到引用标注"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "RAG技术很有效。",
            ["RAG"],
        )
        assert result["citation_score"] == 0.5

    def test_total_score_weighted(self):
        """总分是加权计算"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "根据[1]，RAG是检索增强生成技术。" + "x" * 100,
            ["检索", "增强", "生成"],
        )
        # keyword_score=1.0 * 0.5 + length_score * 0.2 + citation_score=1.0 * 0.3
        assert result["total_score"] >= 0.5  # 至少keyword * 0.5
        assert result["total_score"] <= 1.0

    def test_length_score_capped_at_1(self):
        """长度评分最多为1.0"""
        from evaluate import evaluate_answer

        result = evaluate_answer("x" * 500, ["x"])
        assert result["length_score"] == 1.0

    def test_case_insensitive_keywords(self):
        """关键词匹配不区分大小写"""
        from evaluate import evaluate_answer

        result = evaluate_answer(
            "rag is Retrieval Augmented Generation",
            ["rag", "generation"],
        )
        assert result["hits"] == 2


# ======================================================================
# 8. M9配置项默认值
# ======================================================================

class TestM9Config:
    """测试M9配置项"""

    def test_eval_test_cases_path(self):
        """评测集路径配置正确"""
        from src.config import EVAL_TEST_CASES_PATH
        assert EVAL_TEST_CASES_PATH == "evaluation/test_cases.json"

    def test_eval_results_dir(self):
        """评测结果目录配置正确"""
        from src.config import EVAL_RESULTS_DIR
        assert EVAL_RESULTS_DIR == "evaluation"

    def test_eval_similarity_threshold(self):
        """语义相似度阈值在合理范围"""
        from src.config import EVAL_SIMILARITY_THRESHOLD
        assert isinstance(EVAL_SIMILARITY_THRESHOLD, float)
        assert 0 < EVAL_SIMILARITY_THRESHOLD <= 1.0

    def test_eval_alert_drop_threshold(self):
        """告警阈值在合理范围"""
        from src.config import EVAL_ALERT_DROP_THRESHOLD
        assert isinstance(EVAL_ALERT_DROP_THRESHOLD, float)
        assert 0 < EVAL_ALERT_DROP_THRESHOLD <= 1.0
        assert EVAL_ALERT_DROP_THRESHOLD == 0.05  # 5%

    def test_eval_schedule_hour(self):
        """定时任务小时配置合理"""
        from src.config import EVAL_SCHEDULE_HOUR
        assert isinstance(EVAL_SCHEDULE_HOUR, int)
        assert 0 <= EVAL_SCHEDULE_HOUR <= 23

    def test_eval_schedule_minute(self):
        """定时任务分钟配置合理"""
        from src.config import EVAL_SCHEDULE_MINUTE
        assert isinstance(EVAL_SCHEDULE_MINUTE, int)
        assert 0 <= EVAL_SCHEDULE_MINUTE <= 59


# ======================================================================
# 9. 版本对比功能
# ======================================================================

class TestCompareEvaluations:
    """测试版本对比功能"""

    def test_compare_two_versions(self):
        """对比两个版本的评测结果"""
        from evaluate import compare_evaluations

        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "results"
            results_dir.mkdir()

            # 创建v1结果
            v1_data = {
                "version": "v1",
                "answer_accuracy": 0.75,
                "retrieval_hit_rate": 0.80,
                "citation_accuracy": 0.85,
                "avg_semantic_similarity": 0.70,
            }
            (results_dir / "eval_v1.json").write_text(json.dumps(v1_data))

            # 创建v2结果
            v2_data = {
                "version": "v2",
                "answer_accuracy": 0.85,
                "retrieval_hit_rate": 0.90,
                "citation_accuracy": 0.92,
                "avg_semantic_similarity": 0.82,
            }
            (results_dir / "eval_v2.json").write_text(json.dumps(v2_data))

            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    comp = compare_evaluations("v1", "v2")

                    assert comp["version_a"] == "v1"
                    assert comp["version_b"] == "v2"
                    assert comp["prev_answer_accuracy"] == 0.75
                    assert comp["curr_answer_accuracy"] == 0.85

    def test_compare_missing_version_raises(self):
        """不存在的版本抛出FileNotFoundError"""
        from evaluate import compare_evaluations

        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "results"
            results_dir.mkdir()

            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    with pytest.raises(FileNotFoundError):
                        compare_evaluations("nonexistent_a", "nonexistent_b")


# ======================================================================
# 10. 列出评测版本
# ======================================================================

class TestListEvaluationVersions:
    """测试列出已保存的评测版本"""

    def test_list_versions_empty(self):
        """空目录返回空列表"""
        from evaluate import list_evaluation_versions

        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "results"
            results_dir.mkdir()

            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    versions = list_evaluation_versions()
                    assert versions == []

    def test_list_versions_with_data(self):
        """有数据时返回版本列表"""
        from evaluate import list_evaluation_versions

        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir) / "results"
            results_dir.mkdir()
            (results_dir / "eval_20250101.json").write_text("{}")
            (results_dir / "eval_20250201.json").write_text("{}")
            (results_dir / "eval_20250301.json").write_text("{}")

            with patch("evaluate.BASE_DIR", Path(tmpdir)):
                with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                    versions = list_evaluation_versions()
                    assert len(versions) == 3
                    assert versions == sorted(versions)  # 按字母排序

    def test_list_versions_nonexistent_dir(self):
        """目录不存在时返回空列表"""
        from evaluate import list_evaluation_versions

        with patch("evaluate.BASE_DIR", Path("/nonexistent")):
            with patch("evaluate.EVAL_RESULTS_DIR", "results"):
                versions = list_evaluation_versions()
                assert versions == []


# ======================================================================
# 11. check_retrieval_hit
# ======================================================================

class TestCheckRetrievalHit:
    """测试检索命中检查"""

    def test_hit_when_source_found(self):
        """检索结果包含预期来源时返回True"""
        from evaluate import check_retrieval_hit

        sources = [
            {"content": "这是来自AI应用工程师学习路线图.md的内容"},
            {"content": "更多内容"},
        ]
        assert check_retrieval_hit(sources, ["AI应用工程师学习路线图.md"]) is True

    def test_miss_when_source_not_found(self):
        """检索结果不包含预期来源时返回False"""
        from evaluate import check_retrieval_hit

        sources = [{"content": "无关内容"}]
        assert check_retrieval_hit(sources, ["AI应用工程师学习路线图.md"]) is False

    def test_empty_source_files_returns_true(self):
        """无来源要求时默认命中"""
        from evaluate import check_retrieval_hit

        assert check_retrieval_hit([], []) is True
        assert check_retrieval_hit([{"content": "xxx"}], []) is True


# ======================================================================
# 12. check_citation
# ======================================================================

class TestCheckCitation:
    """测试引用检查"""

    def test_has_citation(self):
        """包含引用标注"""
        from evaluate import check_citation

        assert check_citation("根据[1]，RAG很有效。") is True
        assert check_citation("根据[1][2]，效果很好。") is True
        assert check_citation("研究[1]表明...") is True

    def test_no_citation(self):
        """不包含引用标注"""
        from evaluate import check_citation

        assert check_citation("RAG技术很有效。") is False
        assert check_citation("没有标注的回答") is False
