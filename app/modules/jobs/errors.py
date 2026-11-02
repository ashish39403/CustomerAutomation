class TransientJobError(Exception):
    """Retry with backoff."""


class PermanentJobError(Exception):
    """Move the job to dead; do not retry."""
