import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from typing import Optional


def init_logger(
	name: Optional[str] = None,
	level: str = "INFO",
	log_file: str = "app.log",
	max_bytes: int = 10 * 1024 * 1024,
	backup_count: int = 5,
) -> Logger:
	"""Initialize and return a configured logger.

	Parameters
	- name: Logger name. If None, the root logger is configured.
	- level: Logging level name as a string (e.g., "INFO").
	  The function accepts level names ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
	- log_file: Path to the rotating log file.
	- max_bytes: Maximum bytes per log file before rotation.
	- backup_count: Number of rotated files to keep.

	The function is idempotent: calling it repeatedly for the same
	logger will not add duplicate handlers.
	"""

	logger = logging.getLogger(name)
	logger.setLevel(level)

	# Avoid adding handlers multiple times if init_logger is called more than once
	if logger.handlers:
		return logger

	formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

	# Console handler
	console_handler = logging.StreamHandler()
	console_handler.setLevel(level)
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)

	# Rotating file handler
	try:
		file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
		file_handler.setLevel(level)
		file_handler.setFormatter(formatter)
		logger.addHandler(file_handler)
	except Exception:
		# If file handler cannot be created (permissions, invalid path, etc.),
		# keep going with console-only logging to avoid crashing the app during init.
		logger.exception("Failed to initialize file handler for logger; using console only")

	return logger

