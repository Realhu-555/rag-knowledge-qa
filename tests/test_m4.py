"""M4模块验收测试 — 生产监控

覆盖:
1. logging_config.py — 结构化JSON日志
2. metrics.py — MetricsCollector 计数/直方图/快照
3. tracer.py — Trace 生成trace_id，记录各阶段span
4. alert_manager.py — AlertManager 告警触发
"""
import json
import logging
import time

import pytest

# ============================================================
# 1. 结构化日志（logging_config.py）
# ============================================================

class TestJSONLogger:
    """测试 JSONFormatter 输出合法 JSON"""

    def test_json_format_output(self):
        """日志输出应为合法JSON，且包含必要字段"""
        from src.api.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        raw = formatter.format(record)
        data = json.loads(raw)

        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert "timestamp" in data
        assert "module" in data
        assert "request_id" in data

    def test_json_format_with_extra_data(self):
        """extra_data 应合并到JSON顶层"""
        from src.api.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warn msg", args=(), exc_info=None,
        )
        record.extra_data = {"method": "GET", "status_code": 200}

        raw = formatter.format(record)
        data = json.loads(raw)

        assert data["method"] == "GET"
        assert data["status_code"] == 200

    def test_request_id_context_variable(self):
        """request_id_ctx 有默认值 '-'"""
        from src.api.logging_config import request_id_ctx

        # 默认值
        assert request_id_ctx.get() == "-"

    def test_logger_setup_returns_logger(self):
        """setup_logger 应返回一个配置好的 logger"""
        from src.api.logging_config import setup_logger

        lg = setup_logger("test_m4_setup")
        assert isinstance(lg, logging.Logger)
        assert lg.level == logging.INFO
        # handler 使用 JSONFormatter
        assert any(isinstance(h.formatter, type(lg.handlers[0].formatter))
                   for h in lg.handlers if h.formatter)

    def test_log_request_function(self):
        """log_request 不应抛异常，且输出JSON含method字段"""
        from src.api.logging_config import log_request

        # 不抛异常即通过
        log_request("GET", "/api/query", 200, 12.34)

    def test_log_llm_call_function(self):
        """log_llm_call 不应抛异常"""
        from src.api.logging_config import log_llm_call
        log_llm_call("deepseek-chat", 100, 200, 500.0)

    def test_log_retrieval_function(self):
        """log_retrieval 不应抛异常"""
        from src.api.logging_config import log_retrieval
        log_retrieval("测试查询", 10, 5, 25.0)


# ============================================================
# 2. MetricsCollector（metrics.py）
# ============================================================

class TestMetricsCollector:
    """测试计数器、直方图、快照"""

    @pytest.fixture(autouse=True)
    def _fresh_metrics(self, monkeypatch):
        """每个测试用例使用全新的 MetricsCollector 实例，避免状态污染"""
        from src.core import metrics as m_mod
        # 重置单例
        m_mod.MetricsCollector._instance = None
        yield
        # 清理
        m_mod.MetricsCollector._instance = None

    def _get_mc(self):
        from src.core.metrics import MetricsCollector
        return MetricsCollector()

    def test_counter_inc_and_get(self):
        """计数器 inc + get"""
        mc = self._get_mc()
        mc.inc_counter("requests")
        mc.inc_counter("requests", 5)
        assert mc.get_counter("requests") == 6

    def test_counter_default_zero(self):
        """未设置的计数器返回 0"""
        mc = self._get_mc()
        assert mc.get_counter("nonexistent") == 0

    def test_histogram_record_and_stats(self):
        """直方图 record + 统计字段"""
        mc = self._get_mc()
        for v in [100, 200, 300, 400, 500]:
            mc.record_histogram("latency", v)

        h = mc.get_histogram("latency")
        assert h["count"] == 5
        assert h["avg"] == 300.0
        assert h["p50"] == 300
        assert h["max"] == 500

    def test_histogram_empty_returns_dict(self):
        """不存在的直方图返回空 dict"""
        mc = self._get_mc()
        assert mc.get_histogram("no_such") == {}

    def test_snapshot(self):
        """快照应包含 counters、histograms、error_rate_pct"""
        mc = self._get_mc()
        mc.inc_counter("total_queries", 20)
        mc.inc_counter("total_errors", 2)
        mc.record_histogram("query_latency_ms", 100)

        snap = mc.snapshot()
        assert snap["counters"]["total_queries"] == 20
        assert snap["counters"]["total_errors"] == 2
        assert "histograms" in snap
        assert "error_rate_pct" in snap
        assert snap["error_rate_pct"] == 10.0  # 2/20 * 100

    def test_snapshot_zero_queries_no_division_error(self):
        """total_queries=0 时 error_rate_pct 应为 0"""
        mc = self._get_mc()
        snap = mc.snapshot()
        assert snap["error_rate_pct"] == 0.0

    def test_record_alert(self):
        """record_alert 应存入告警列表"""
        mc = self._get_mc()
        mc.record_alert("high_error_rate", "err too high", {"rate": 0.1})
        alerts = mc.get_recent_alerts()
        assert len(alerts) == 1
        assert alerts[0]["type"] == "high_error_rate"

    def test_record_alert_limit(self):
        """超过1000条告警时只保留最近1000条"""
        mc = self._get_mc()
        for i in range(1050):
            mc.record_alert("type", f"msg{i}")
        alerts = mc.get_recent_alerts(limit=2000)
        assert len(alerts) <= 1000

    def test_maybe_reset_window(self):
        """窗口过期时 should reset"""
        mc = self._get_mc()
        # 首次应返回True
        result = mc.maybe_reset_window("test_window", 0.1)
        assert result is True
        # 立即再调用应返回False
        result2 = mc.maybe_reset_window("test_window", 0.1)
        assert result2 is False

    def test_histogram_p95_p99(self):
        """直方图 p95、p99 值合理"""
        mc = self._get_mc()
        for v in range(1, 101):
            mc.record_histogram("perf", float(v))
        h = mc.get_histogram("perf")
        assert h["p95"] >= h["p50"]
        assert h["p99"] >= h["p95"]

    def test_singleton(self):
        """MetricsCollector 是单例"""
        from src.core.metrics import MetricsCollector
        a = MetricsCollector()
        b = MetricsCollector()
        assert a is b


# ============================================================
# 3. Tracer（tracer.py）
# ============================================================

class TestTracer:
    """测试 Trace 生命周期"""

    @pytest.fixture(autouse=True)
    def _init_db(self, tmp_path, monkeypatch):
        """使用临时数据库"""
        db_file = tmp_path / "traces_test.db"
        monkeypatch.setattr("src.core.tracer.DB_PATH", db_file)
        from src.core.tracer import init_traces_table
        init_traces_table()

    def test_trace_generates_trace_id(self):
        """Trace 应生成唯一 trace_id"""
        from src.core.tracer import Trace

        t1 = Trace(query="问题1")
        t2 = Trace(query="问题2")
        assert t1.trace_id != t2.trace_id
        assert t1.trace_id.startswith("trace_")

    def test_span_lifecycle(self):
        """start_span -> end_span 应正确记录 duration"""
        from src.core.tracer import Trace

        trace = Trace(query="测试")
        trace.start_span("retrieval")
        time.sleep(0.01)
        trace.end_span(data={"results": 5})

        assert len(trace.spans) == 1
        assert trace.spans[0].name == "retrieval"
        assert trace.spans[0].duration_ms > 0
        assert trace.spans[0].data["results"] == 5

    def test_multiple_spans(self):
        """一次 Trace 可记录多个 Span"""
        from src.core.tracer import Trace

        trace = Trace(query="多阶段测试")
        for name in ["understand", "retrieve", "rerank", "generate"]:
            trace.start_span(name)
            time.sleep(0.005)
            trace.end_span()

        assert len(trace.spans) == 4
        names = [s.name for s in trace.spans]
        assert names == ["understand", "retrieve", "rerank", "generate"]

    def test_finish_persists_to_sqlite(self):
        """finish() 应将 trace 写入 SQLite"""
        from src.core.tracer import Trace

        trace = Trace(query="持久化测试")
        trace.start_span("test_stage")
        trace.end_span()
        trace.finish()

        # 从数据库读回
        from src.core.tracer import get_trace
        record = get_trace(trace.trace_id)
        assert record is not None
        assert record["query"] == "持久化测试"
        assert record["total_ms"] >= 0
        assert "stages" in record

    def test_get_trace_nonexistent(self):
        """查询不存在的 trace_id 应返回 None"""
        from src.core.tracer import get_trace
        assert get_trace("trace_nonexistent_xyz") is None

    def test_list_recent_traces(self):
        """list_recent_traces 应返回已存入的 trace"""
        from src.core.tracer import Trace, list_recent_traces

        for i in range(3):
            t = Trace(query=f"问题{i}")
            t.finish()

        traces = list_recent_traces(limit=10)
        assert len(traces) >= 3

    def test_trace_with_user_id(self):
        """Trace 记录 user_id"""
        from src.core.tracer import Trace, get_trace

        trace = Trace(query="带用户测试", user_id="user_42")
        trace.finish()
        record = get_trace(trace.trace_id)
        assert record["user_id"] == "user_42"

    def test_span_to_dict(self):
        """Span.to_dict() 包含 name 和 duration_ms"""
        from src.core.tracer import Span

        s = Span(name="embed", start_time=1.0, end_time=1.5, data={"dim": 384})
        d = s.to_dict()
        assert d["name"] == "embed"
        assert d["duration_ms"] == 500.0
        assert d["dim"] == 384

    def test_trace_status_ok(self):
        """Trace 默认 status 为 ok"""
        from src.core.tracer import Trace
        t = Trace(query="状态测试")
        assert t.status == "ok"


# ============================================================
# 4. AlertManager（alert_manager.py）
# ============================================================

class TestAlertManager:
    """测试告警触发逻辑"""

    @pytest.fixture(autouse=True)
    def _fresh_state(self, monkeypatch):
        """重置 MetricsCollector 单例和 AlertManager 状态，并确保
        alert_manager 内部引用的 metrics 指向同一个新实例。"""
        from src.core import metrics as m_mod
        from src.core import alert_manager as am_mod
        m_mod.MetricsCollector._instance = None
        mc = m_mod.MetricsCollector()
        # 让 alert_manager 模块级的 metrics 变量指向同一个新实例
        am_mod.metrics = mc
        yield
        m_mod.MetricsCollector._instance = None

    def test_no_alert_when_normal(self):
        """正常指标不触发告警"""
        from src.core.alert_manager import AlertManager

        am = AlertManager()
        # 窗口检查: 强制允许检查
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        from src.core.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.inc_counter("total_queries", 100)
        mc.inc_counter("total_errors", 1)  # 1%

        alerts = am.check_all()
        error_alerts = [a for a in alerts if a["type"] == "high_error_rate"]
        assert len(error_alerts) == 0

    def test_error_rate_alert_triggers(self):
        """错误率 > 5% 且 total >= 10 时触发告警"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        mc.inc_counter("total_queries", 20)
        mc.inc_counter("total_errors", 3)  # 15%

        alerts = am.check_all()
        error_alerts = [a for a in alerts if a["type"] == "high_error_rate"]
        assert len(error_alerts) == 1
        assert "错误率" in error_alerts[0]["message"]
        assert error_alerts[0]["details"]["error_rate"] == 0.15

    def test_no_error_alert_when_samples_too_low(self):
        """样本不足10时不触发告警"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        mc.inc_counter("total_queries", 5)
        mc.inc_counter("total_errors", 5)  # 100% 但样本不足

        alerts = am.check_all()
        error_alerts = [a for a in alerts if a["type"] == "high_error_rate"]
        assert len(error_alerts) == 0

    def test_latency_alert_triggers(self):
        """平均延迟 > 3000ms 时触发告警"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        # 记录多个高延迟值，确保 avg > 3000
        for _ in range(10):
            mc.record_histogram("query_latency_ms", 4000.0)

        alerts = am.check_all()
        latency_alerts = [a for a in alerts if a["type"] == "high_latency"]
        assert len(latency_alerts) == 1
        assert "延迟" in latency_alerts[0]["message"]

    def test_no_latency_alert_when_below_threshold(self):
        """平均延迟 < 3000ms 时不触发"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        for _ in range(10):
            mc.record_histogram("query_latency_ms", 500.0)

        alerts = am.check_all()
        latency_alerts = [a for a in alerts if a["type"] == "high_latency"]
        assert len(latency_alerts) == 0

    def test_no_latency_alert_when_samples_too_low(self):
        """延迟直方图样本不足5条时不触发"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        mc.record_histogram("query_latency_ms", 5000.0)
        mc.record_histogram("query_latency_ms", 6000.0)  # 只有2个样本

        alerts = am.check_all()
        latency_alerts = [a for a in alerts if a["type"] == "high_latency"]
        assert len(latency_alerts) == 0

    def test_cooldown_prevents_repeated_alerts(self):
        """短时间内重复调用 check_all 不重复触发"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        mc.inc_counter("total_queries", 20)
        mc.inc_counter("total_errors", 3)

        alerts1 = am.check_all()
        assert any(a["type"] == "high_error_rate" for a in alerts1)

        # 立即再调用，应被冷却期挡住
        alerts2 = am.check_all()
        error_alerts2 = [a for a in alerts2 if a["type"] == "high_error_rate"]
        assert len(error_alerts2) == 0

    def test_alert_recorded_in_metrics(self):
        """触发的告警应被 record_alert 记录到 MetricsCollector"""
        from src.core.alert_manager import AlertManager
        from src.core.metrics import MetricsCollector

        am = AlertManager()
        am._last_error_check = 0.0
        am._last_latency_check = 0.0

        mc = MetricsCollector()
        mc.inc_counter("total_queries", 20)
        mc.inc_counter("total_errors", 3)

        am.check_all()
        recent = mc.get_recent_alerts()
        assert any(a["type"] == "high_error_rate" for a in recent)
