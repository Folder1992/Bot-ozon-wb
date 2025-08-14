
import logging, os, sys
def setup_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    root = logging.getLogger()
    if getattr(setup_logging, "_configured", False):
        root.setLevel(level)
        return
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter(fmt))
    root.handlers[:] = [h]
    root.setLevel(level)
    setup_logging._configured = True
