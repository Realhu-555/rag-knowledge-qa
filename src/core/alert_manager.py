"""告警管理器 — M4生产监控

规则：
  - 错误率 > 5%（1分钟窗口）→ 告警
  - 平均延迟 > 3000ms（5分钟窗口）→ 告警
"""
import time

from src.core.metrics import metrics
from src.api.logging_config import logger
from src.config import (
    ALERT_ERROR_RATE_THRESHOLD,
    ALERT_LATENCY_THRESHOLD_MS,
    ALERT_CHECK_WINDOW_SECONDS,
    ALERT_LATENCY_WINDOW_SECONDS,
)


class AlertManager:
    """定时检查指标，触发告警"""

    def __init__(self) -> None:
        self._last_error_check = 0.0
        self._last_latency_check = 0.0

    def check_all(self) -> list[dict]:
        """执行所有告警规则，返回本次触发的告警列表"""
        alerts: list[dict] = []
        alerts.extend(self._check_error_rate())
        alerts.extend(self._check_latency())
        return alerts

    # ------------------------------------------------------------------
    # 规则：错误率
    # ------------------------------------------------------------------

    def _check_error_rate(self) -> list[dict]:
        now = time.time()
        if now - self._last_error_check < ALERT_CHECK_WINDOW_SECONDS:
            return []
        self._last_error_check = now

        # 窗口到期时重置直方图
        metrics.maybe_reset_window("error_rate", ALERT_CHECK_WINDOW_SECONDS)

        total = metrics.get_counter("total_queries")
        errors = metrics.get_counter("total_errors")
        if total < 10:
            # 样本太少不告警
            return []

        error_rate = errors / total
        if error_rate > ALERT_ERROR_RATE_THRESHOLD:
            msg = (f"错误率 {error_rate*100:.1f}% 超过阈值 "
                   f"{ALERT_ERROR_RATE_THRESHOLD*100:.0f}% "
                   f"（{errors}/{total}）")
            alert = {
                "type": "high_error_rate",
                "message": msg,
                "timestamp": now,
                "details": {"error_rate": error_rate, "errors": errors, "total": total},
            }
            metrics.record_alert("high_error_rate", msg, alert["details"])
            logger.warning(f"ALERT: {msg}")
            return [alert]
        return []

    # ------------------------------------------------------------------
    # 规则：延迟
    # ------------------------------------------------------------------

    def _check_latency(self) -> list[dict]:
        now = time.time()
        if now - self._last_latency_check < ALERT_LATENCY_WINDOW_SECONDS:
            return []
        self._last_latency_check = now

        hist = metrics.get_histogram("query_latency_ms")
        if not hist or hist.get("count", 0) < 5:
            return []

        avg_ms = hist["avg"]
        if avg_ms > ALERT_LATENCY_THRESHOLD_MS:
            msg = (f"平均查询延迟 {avg_ms:.0f}ms 超过阈值 "
                   f"{ALERT_LATENCY_THRESHOLD_MS}ms")
            alert = {
                "type": "high_latency",
                "message": msg,
                "timestamp": now,
                "details": {"avg_latency_ms": avg_ms, "threshold_ms": ALERT_LATENCY_THRESHOLD_MS},
            }
            metrics.record_alert("high_latency", msg, alert["details"])
            logger.warning(f"ALERT: {msg}")
            return [alert]
        return []


# 全局单例
alert_manager = AlertManager()
