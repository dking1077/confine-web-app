import logging
import sys


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging():
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [request_id=%(request_id)s] %(message)s")
    )
    handler.addFilter(RequestIDFilter())

    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Celery
    logging.getLogger("celery").setLevel(logging.ERROR)
    logging.getLogger("celery.app.trace").setLevel(logging.ERROR)
    logging.getLogger("celery.worker").setLevel(logging.ERROR)
    logging.getLogger("celery.worker.strategy").setLevel(logging.ERROR)