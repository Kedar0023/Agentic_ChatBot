import logging
import sys
# from pathlib import Path
# Path("logs").mkdir(exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)

formatter = logging.Formatter(LOG_FORMAT)

logger = logging.getLogger("fastapi_app")
logger.setLevel(logging.INFO)

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(formatter)

# _file_handler = logging.FileHandler("logs/app.log")
# _file_handler.setFormatter(formatter)

logger.addHandler(_stream_handler)
# logger.addHandler(_file_handler)
