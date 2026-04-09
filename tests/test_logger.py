"""Tests for logging helpers."""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.similar_user.utils import logger as logger_module


class LoggerTest(unittest.TestCase):
    def test_setup_logging_adds_console_and_file_handlers_once(self) -> None:
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_log_dir = Path(temp_dir) / "logs"
            with patch.object(logger_module, "LOG_DIR", temp_log_dir), patch.object(
                logger_module,
                "LOG_FILE",
                temp_log_dir / "similar_user.log",
            ):
                try:
                    root_logger.handlers = []
                    logger_module.setup_logging()
                    self.assertEqual(len(root_logger.handlers), 2)

                    logger_module.setup_logging()
                    self.assertEqual(len(root_logger.handlers), 2)
                finally:
                    for handler in root_logger.handlers:
                        handler.close()
                    root_logger.handlers = original_handlers
                    root_logger.setLevel(original_level)

    def test_get_logger_returns_named_logger(self) -> None:
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        original_level = root_logger.level

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_log_dir = Path(temp_dir) / "logs"
            with patch.object(logger_module, "LOG_DIR", temp_log_dir), patch.object(
                logger_module,
                "LOG_FILE",
                temp_log_dir / "similar_user.log",
            ):
                try:
                    root_logger.handlers = []
                    logger = logger_module.get_logger("similar_user.test")
                    self.assertEqual(logger.name, "similar_user.test")
                finally:
                    for handler in root_logger.handlers:
                        handler.close()
                    root_logger.handlers = original_handlers
                    root_logger.setLevel(original_level)


if __name__ == "__main__":
    unittest.main()
