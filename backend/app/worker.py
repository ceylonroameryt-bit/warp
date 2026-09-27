"""
Warp Ladger — ARQ Worker Entry Point
Run with: python -m app.worker (or arq app.worker.WorkerSettings)

This worker processes background jobs:
- invoice.generate_pdf
- invoice.send_email
"""
import os
from arq.connections import RedisSettings
from app.invoices.tasks import generate_pdf_task, send_email_task
from app.documents.tasks import process_document_task


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [generate_pdf_task, send_email_task, process_document_task]

    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )

    max_jobs = 10
    job_timeout = 120         # seconds per job
    keep_result = 3600        # keep result in Redis for 1 hour
    max_tries = 3             # max retries per job
    retry_delay = 30.0        # seconds between retries

    on_startup = None
    on_shutdown = None


if __name__ == "__main__":
    import asyncio
    from arq import run_worker
    asyncio.run(run_worker(WorkerSettings))
