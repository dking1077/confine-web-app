from app.extensions import celery
from app.celery import signals
from app import create_app
from config import Config
import logging

logger = logging.getLogger(__name__)

# Create and initialize the app with Celery
app = create_app(Config)