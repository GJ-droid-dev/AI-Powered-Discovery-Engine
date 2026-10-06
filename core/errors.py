"""Custom exception hierarchy for the Discovery Engine pipeline.

Error Severity Levels:
    SKIP    - Single record failure. Log, skip record, continue.
    RETRY   - Transient API failure. Retry 3x with backoff.
    DEGRADE - Source-level failure. Skip source, warn in report.
    HALT    - Critical failure. Stop pipeline, surface error.
"""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(self, message: str, error_code: str = "UNKNOWN", stage: str = "unknown", record_id: str | None = None):
        self.error_code = error_code
        self.stage = stage
        self.record_id = record_id
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "stage": self.stage,
            "error_code": self.error_code,
            "record_id": self.record_id,
            "message": str(self),
        }


class SkipRecordError(PipelineError):
    """Single record failure — log and skip, pipeline continues.

    Examples: bad parse, LLM refusal for one record, malformed text.
    """

    def __init__(self, message: str, record_id: str | None = None, stage: str = "unknown"):
        super().__init__(message, error_code="SKIP_RECORD", stage=stage, record_id=record_id)


class RetryableError(PipelineError):
    """Transient failure — should be retried with exponential backoff.

    Examples: API rate limit, network timeout, temporary service outage.
    """

    def __init__(self, message: str, stage: str = "unknown", retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message, error_code="RETRYABLE", stage=stage)


class SourceDegradedError(PipelineError):
    """Entire data source is unavailable — skip source, warn in report.

    Examples: Reddit API down, scraper blocked, credentials invalid.
    """

    def __init__(self, message: str, source_type: str, stage: str = "collector"):
        self.source_type = source_type
        super().__init__(message, error_code="SOURCE_UNAVAILABLE", stage=stage)


class PipelineHaltError(PipelineError):
    """Critical failure — stop the entire pipeline immediately.

    Examples: no LLM access, config file missing, data directory inaccessible.
    """

    def __init__(self, message: str, stage: str = "unknown"):
        super().__init__(message, error_code="PIPELINE_HALT", stage=stage)


class LLMError(RetryableError):
    """LLM API call failed — retryable by default.

    Examples: timeout, rate limit, invalid response format.
    """

    def __init__(self, message: str, stage: str = "analysis", raw_response: str | None = None):
        self.raw_response = raw_response
        super().__init__(message, stage=stage)
        self.error_code = "LLM_ERROR"


class ParseError(SkipRecordError):
    """Raw text could not be parsed or normalized."""

    def __init__(self, message: str, record_id: str | None = None, stage: str = "normalizer"):
        super().__init__(message, record_id=record_id, stage=stage)
        self.error_code = "PARSE_FAILURE"


class ClassificationUncertainError(SkipRecordError):
    """The model could not confidently classify the feedback."""

    def __init__(self, message: str, record_id: str | None = None, confidence: float = 0.0):
        self.confidence = confidence
        super().__init__(message, record_id=record_id, stage="analysis")
        self.error_code = "CLASSIFICATION_UNCERTAIN"
