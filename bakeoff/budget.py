"""Thread-safe request reservations; a conservative cost estimate, not a billing cap."""

from decimal import Decimal
import threading

# Standard uncached text rates, USD per million tokens, checked 2026-11-15.
# https://developers.openai.com/api/docs/models
RATES = {
    "gpt-6-astra": (Decimal("10"), Decimal("50")),
    "gpt-6.1-sol": (Decimal("2"), Decimal("10")),
    "gpt-6.1-terra": (Decimal("1"), Decimal("5")),
    "gpt-6-luna": (Decimal("0.1"), Decimal("0.5")),
    "gpt-6-sol": (Decimal("2"), Decimal("10")),
}


class BudgetExceeded(Exception):
    pass


class RaceBudget:
    def __init__(self, dollars="2.00", max_calls=20):
        self.limit = Decimal(str(dollars))
        if not self.limit.is_finite() or self.limit <= 0 or not 1 <= max_calls <= 20:
            raise ValueError("Budget must be positive and max_calls must be 1 through 20.")
        self.max_calls = max_calls
        self.calls = 0
        self.accounted = Decimal(0)
        self.reserved = Decimal(0)
        self.unknown_requests = 0
        self.lock = threading.Lock()

    def reserve(self, model, input_bytes, output_limit):
        input_rate, output_rate = RATES[model]
        # Budget pessimistically at one token per UTF-8 byte plus protocol overhead.
        # This is an estimate, not an API-guaranteed token count.
        reserve = ((input_bytes + 2048) * input_rate + output_limit * output_rate) / 1_000_000
        with self.lock:
            if self.calls >= self.max_calls or self.accounted + self.reserved + reserve > self.limit:
                raise BudgetExceeded("The shared request/cost reservation limit was reached.")
            self.calls += 1
            self.reserved += reserve
        return model, reserve

    def settle(self, ticket, usage):
        model, reserve = ticket
        with self.lock:
            self.reserved -= reserve
            if usage is None:
                self.accounted += reserve
                self.unknown_requests += 1
            else:
                incoming, outgoing = RATES[model]
                self.accounted += (usage.input_tokens * incoming + usage.output_tokens * outgoing) / 1_000_000

    def snapshot(self):
        with self.lock:
            return {"estimated_limit_usd": str(self.limit), "calls_started": self.calls,
                    "max_calls": self.max_calls, "accounted_estimated_usd": str(self.accounted),
                    "reserved_estimated_usd": str(self.reserved), "unknown_requests": self.unknown_requests,
                    "rates_checked": "2026-11-15", "is_provider_billing_cap": False}
