class BillingClock:
    """Iteration-driven billing clock.

    Tracks simulated elapsed days as a counter advanced explicitly by the
    experiment each iteration (one call to set_elapsed per step). This decouples
    simulated time from wall-clock speed so the billing period always spans
    exactly total_days iterations regardless of LLM latency.
    """

    def __init__(self, total_days: int = 30):
        self.total_days = total_days
        self._elapsed_days: float = 0.0

    def set_elapsed(self, days: float) -> None:
        self._elapsed_days = float(days)

    @property
    def elapsed_days(self) -> float:
        return self._elapsed_days

