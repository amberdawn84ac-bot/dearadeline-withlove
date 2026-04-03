"""Structured logging utility for production debugging."""
import logging
from typing import Optional


class StructuredLogFormatter(logging.Formatter):
    """Formatter that includes context in every log message."""

    def __init__(self, context: Optional[dict] = None):
        super().__init__()
        self.context = context or {}

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with context fields included.

        Output format: [CONTEXT] message
        Example: [student_id=abc track=HISTORY] Document not found
        """
        # Build context string
        context_parts = []
        for key, value in self.context.items():
            if value is not None:
                context_parts.append(f"{key}={value}")

        context_str = " ".join(context_parts)

        # Format message
        if context_str:
            return f"[{context_str}] {record.getMessage()}"
        return record.getMessage()


class StructuredLogger(logging.Logger):
    """Custom logger that applies structured formatting to all handlers."""

    def __init__(self, name: str, context: Optional[dict] = None):
        super().__init__(name)
        self._structured_context = context or {}

    def addHandler(self, hdlr):
        """Override addHandler to apply structured formatting."""
        # Apply structured formatter to the handler
        if not isinstance(hdlr.formatter, StructuredLogFormatter):
            hdlr.setFormatter(StructuredLogFormatter(context=self._structured_context))
        super().addHandler(hdlr)

    def setFormatter(self, formatter):
        """Override to ensure structured formatting is always applied."""
        # This prevents external code from replacing our structured formatter
        pass


def get_structured_logger(
    name: str,
    student_id: Optional[str] = None,
    track: Optional[str] = None,
    archive_name: Optional[str] = None,
    similarity_score: Optional[float] = None,
) -> logging.Logger:
    """
    Get a logger with structured context fields.

    Args:
        name: Logger name
        student_id: Student ID for context (optional)
        track: Track name (e.g., TRUTH_HISTORY) for context (optional)
        archive_name: Archive name (e.g., NARA) for context (optional)
        similarity_score: Similarity score for context (optional)

    Returns:
        Logger with structured formatting

    Example:
        logger = get_structured_logger(
            name="seed_nara",
            track="TRUTH_HISTORY",
            archive_name="NARA",
        )
        logger.info("Seeding documents")
        # Output: [track=TRUTH_HISTORY archive_name=NARA] Seeding documents
    """
    # Create context dict
    context = {
        "student_id": student_id,
        "track": track,
        "archive_name": archive_name,
        "similarity_score": similarity_score,
    }

    # Remove None values to keep output clean
    context = {k: v for k, v in context.items() if v is not None}

    # Set the logger class and create the logger
    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger(name)

    # Initialize with context if this is a new instance
    if isinstance(logger, StructuredLogger) and not hasattr(logger, '_context_set'):
        logger.__init__(name, context=context)
        logger._context_set = True

    # Create formatter with context and apply to existing handlers
    formatter = StructuredLogFormatter(context=context)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setFormatter(formatter)

    return logger
