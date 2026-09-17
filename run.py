from app import create_app
from config import Config
import logging
import os
import debugpy

logger = logging.getLogger(__name__)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    logger.info("\n\n=== FLASK RELOADED ===\n\n")
else:
    logger.info("\n\n=== FLASK INITIAL START ===\n\n")

if os.getenv("DEBUGPY") == "1" and os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    debugpy.listen(("0.0.0.0", 5678))
    logger.info("debugpy listening on 5678")

app = create_app(Config)
logger.info("===== WEB STARTED =====")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)




