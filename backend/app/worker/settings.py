from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.worker.tasks import heartbeat, process_due_pac_plans, process_due_recurring_rules


async def on_startup(ctx: dict[Any, Any]) -> None:
    _ = ctx
    configure_logging()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [
        heartbeat,
        process_due_recurring_rules,
        process_due_pac_plans,
    ]
    cron_jobs: ClassVar[list[Any]] = [
        cron(process_due_recurring_rules, hour=1, minute=0),
        cron(process_due_pac_plans, hour=1, minute=15),
    ]
    on_startup = on_startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
