"""
Module: test_logging.py

Author: Michael Economou
Date: 2025-05-31

test_logging.py
Tests the logging system setup to verify:
- General logs (info/debug) go to oncutf_activity.log
- Errors go to oncutf_errors.log
- Rename logs go only to rename.log if filtered
Run this after setting up init_logging and logger_file_helper.
"""
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*never awaited')
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)

"""
test_logging.py

Tests the logging system setup to verify:
- General logs (info/debug) go to oncutf_activity.log
- Errors go to oncutf_errors.log
- Rename logs go only to rename.log if filtered

Run this after setting up init_logging and logger_file_helper.

"""

import logging
import os

from utils.init_logging import init_logging
from utils.logger_file_helper import add_file_handler


# Clean log files (for test only)
def clean_logs():
    for filename in [
        "logs/oncutf_activity.log",
        "logs/oncutf_errors.log",
        "logs/rename.log"
    ]:
        if os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("")

# Run test logging
def run_tests():
    logger = init_logging("oncutf")
    logger.info("[TEST] Application log test - info")
    logger.debug("[TEST] Application log test - debug")
    logger.warning("[TEST] Application log test - warning")
    logger.error("Application log test - error")
    logger.critical("[TEST] Application log test - critical")

    # Setup rename logger separately
    rename_logger = logging.getLogger("rename")
    rename_logger.propagate = False  # prevent logs going to root handlers
    add_file_handler(rename_logger, "logs/rename.log", level=20, filter_by_name="rename")

    rename_logger.debug("🧪 Rename logger — debug")
    rename_logger.info("🧪 Rename logger — info")
    rename_logger.warning("🧪 Rename logger — warning")

if __name__ == "__main__":
    clean_logs()
    run_tests()
