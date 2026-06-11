"""M9: 评测定时任务 — APScheduler 定时运行评测 + 质量下降告警"""
import json
import logging
from datetime import datetime

from src.config import (
    EVAL_SCHEDULE_HOUR,
    EVAL_SCHEDULE_MINUTE,
    EVAL_ALERT_DROP_THRESHOLD,
)

logger = logging.getLogger(__name__)


def run_scheduled_evaluation() -> dict:
    """执行定时评测并检查是否需要告警

    Returns:
        评测汇总结果字典
    """
    from evaluate import run_evaluation, save_to_database
    from src.storage.database import (
        get_latest_evaluation,
        get_previous_evaluation,
    )

    logger.info("定时评测开始执行")

    version = datetime.now().strftime("scheduled_%Y%m%d_%H%M%S")
    summary = run_evaluation(version=version)

    if "error" in summary:
        logger.error("定时评测执行失败: %s", summary["error"])
        return summary

    # 保存到数据库
    save_to_database(summary)

    # 检查准确率是否下降超过阈值
    _check_quality_alert(summary)

    logger.info(
        "定时评测完成 — 准确率: %.1f%%, 语义相似度: %.3f",
        summary.get("answer_accuracy", 0) * 100,
        summary.get("avg_semantic_similarity", 0),
    )
    return summary


def _check_quality_alert(current_summary: dict) -> None:
    """检查准确率是否下降超过阈值，触发告警"""
    current_accuracy = current_summary.get("answer_accuracy", 0)

    # 从数据库获取上一次评测结果
    try:
        from src.storage.database import get_previous_evaluation
        prev = get_previous_evaluation()
    except Exception:
        prev = None

    if prev is None:
        logger.info("首次评测，无历史数据可对比")
        return

    prev_accuracy = prev.get("answer_accuracy", 0)
    drop = prev_accuracy - current_accuracy

    if drop > EVAL_ALERT_DROP_THRESHOLD:
        alert_msg = (
            f"[告警] 评测准确率下降超过阈值！"
            f" 上次: {prev_accuracy:.1%} → 本次: {current_accuracy:.1%}"
            f" (下降 {drop:.1%}，阈值: {EVAL_ALERT_DROP_THRESHOLD:.1%})"
        )
        logger.warning(alert_msg)
        _send_alert(alert_msg)
    else:
        logger.info(
            "准确率正常 — 上次: %.1%%, 本次: %.1%%, 变化: %+.1%%",
            prev_accuracy * 100,
            current_accuracy * 100,
            -drop * 100,
        )


def _send_alert(message: str) -> None:
    """发送告警通知

    当前实现：日志输出。可扩展为 webhook/email/钉钉/飞书通知。
    """
    logger.warning("ALERT: %s", message)

    # TODO: 可扩展为 webhook 通知
    # import requests
    # webhook_url = os.getenv("ALERT_WEBHOOK_URL", "")
    # if webhook_url:
    #     requests.post(webhook_url, json={"text": message})


def create_scheduler():
    """创建并配置 APScheduler 调度器

    Returns:
        APScheduler 的 BackgroundScheduler 实例
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()

    trigger = CronTrigger(
        hour=EVAL_SCHEDULE_HOUR,
        minute=EVAL_SCHEDULE_MINUTE,
    )

    scheduler.add_job(
        run_scheduled_evaluation,
        trigger=trigger,
        id="daily_evaluation",
        name="每日自动评测",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "评测定时任务已配置 — 每天 %02d:%02d 执行",
        EVAL_SCHEDULE_HOUR,
        EVAL_SCHEDULE_MINUTE,
    )
    return scheduler


def start_scheduler():
    """启动调度器（非阻塞，后台线程运行）"""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("评测调度器已启动")
    return scheduler


if __name__ == "__main__":
    # 直接运行时手动执行一次评测
    logging.basicConfig(level=logging.INFO)
    result = run_scheduled_evaluation()
    print(json.dumps(
        {k: v for k, v in result.items() if k != "results"},
        ensure_ascii=False,
        indent=2,
    ))
