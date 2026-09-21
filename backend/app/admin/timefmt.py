from datetime import datetime, timedelta, timezone

# 中国无夏令时，固定东八区即可，不依赖系统时区库。
CN_TZ = timezone(timedelta(hours=8))


def format_cn_time(value: datetime | None) -> str:
    """把库存的 UTC 时间格式化成东八区展示。无时区的值按 UTC 处理。"""
    if value is None:
        return ""
    if not isinstance(value, datetime):
        return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
