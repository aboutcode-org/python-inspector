#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/python-inspector for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Tuple, Type, Union

# Add TRACE custom level to be third leve, as verbose will match
# -v == logLevel INFO
# -vv == logLevel DEBUG
# -vvv == logLevel TRACE
TRACE_LEVEL: int = 5
DEEP_LEVEL: int = 4


class CustomLogger(logging.Logger):
    def trace(
        self: logging.Logger,
        msg: Any,
        *args: Any,
        exc_info: Union[
            bool,
            BaseException,
            Tuple[Type[BaseException], BaseException, TracebackType],
            None,
        ] = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(
                TRACE_LEVEL,
                msg,
                args,
                exc_info=exc_info,
                extra=extra,
                stack_info=stack_info,
                stacklevel=stacklevel,
            )

    def deep(
        self: logging.Logger,
        msg: Any,
        *args: Any,
        exc_info: Union[
            bool,
            BaseException,
            Tuple[Type[BaseException], BaseException, TracebackType],
            None,
        ] = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        if self.isEnabledFor(DEEP_LEVEL):
            self._log(
                DEEP_LEVEL,
                msg,
                args,
                exc_info=exc_info,
                extra=extra,
                stack_info=stack_info,
                stacklevel=stacklevel,
            )

    logging.Logger.trace = trace
    logging.Logger.deep = deep


def setup_logger(level: str = "WARNING", log_file: Optional[Path] = None) -> None:
    """
    Configure the logger for the 'python-inspector' application.

    This function sets up a custom logging level, assigns a custom logger class,
    and configures the logger with the specified logging level. If no handlers are present,
    it adds a stream handler with a simple formatter.

    Args:
        level (str): The logging level to set for the logger (e.g., 'DEBUG', 'INFO', 'WARNING', "TRACE").
        log_file (Optional[Path]): File name for persistent log

    """
    # Setup out trace level
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.addLevelName(DEEP_LEVEL, "DEEP")
    logging.setLoggerClass(CustomLogger)

    _logger = logging.getLogger("python-inspector")
    _logger.setLevel(level)
    _logger.propagate = False

    if not _logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        _logger.addHandler(handler)

        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)


# Logger as a singleton
logger: logging.Logger = logging.getLogger("python-inspector")
