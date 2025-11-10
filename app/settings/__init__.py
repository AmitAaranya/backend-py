from .config import TITLE, VERSION, EnvInit
from .logging import init_logger


__all__ = ["TITLE", "VERSION", "ENV", "logger"]



ENV = EnvInit()
logger = init_logger(name="app", level=ENV.LOG_LEVEL)