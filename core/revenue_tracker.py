"""
Revenue Tracker — Real revenue tracking for DOF monetization.

Tracks all income sources: SaaS, grants, bounties, freelance,
API usage, consulting, content, templates.
Persists to JSONL. Zero external dependencies.
"""

import os
import json
import time
import uuid
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

logger = logging.getLogger("core.revenue_tracker")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVENUE_DIR = os.path.join(BASE_DIR, "logs", "revenue")
REVENUE_LOG = os.path.join(REVENUE_DIR, "revenue.jsonl")
USAGE_LOG = os.path.join(REVENUE_DIR, "api_usage.jsonl")


@dataclass
class RevenueEntry:
    """A single revenue record."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = ""           # saas, grant, bounty, freelance, consulting, content, template, api
    amount: float = 0.0
    currency: str = "USD"
    description: str = ""
    client: str = ""
    payment_method: str = ""   # stripe, x402, lightning, paypal, crypto, bank
    status: str = "confirmed"  # confirmed, pending, failed
    timestamp: str = ""
    agent: str = ""            # which agent generated this revenue

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class APIUsageEntry:
    """Track API call for usage-based billing."""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    endpoint: str = ""
    caller: str = ""           # API key or agent ID
    tokens_used: int = 0
    cost_estimate: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class RevenueTracker:
    """Track all DOF revenue streams and API usage.

    Supports: track, report, usage logging, stats.
    All data persisted to JSONL.
    """

    def __init__(self):
        os.makedirs(REVENUE_DIR, exist_ok=True)

    def track(self, source: str, amount: float, currency: str = "USD",
              description: str = "", client: str = "",
              payment_method: str = "", agent: str = "") -> RevenueEntry:
        """Record a revenue event."""
        entry = RevenueEntry(
            source=source, amount=amount, currency=currency,
            description=description, client=client,
            payment_method=payment_method, agent=agent,
        )
        self._append(REVENUE_LOG, asdict(entry))
        logger.info(f"Revenue tracked: {source} ${amount:.2f} {currency}")
        return entry

    def log_api_usage(self, endpoint: str, caller: str = "",
                      tokens_used: int = 0, cost_per_token: float = 0.00001) -> APIUsageEntry:
        """Log an API call for usage-based billing."""
        entry = APIUsageEntry(
            endpoint=endpoint, caller=caller,
            tokens_used=tokens_used,
            cost_estimate=tokens_used * cost_per_token,
        )
        self._append(USAGE_LOG, asdict(entry))
        return entry

    def report(self, days: int = 30) -> dict:
        """Generate revenue report for last N days."""
        entries = self._load(REVENUE_LOG)
        cutoff = time.time() - (days * 86400)

        filtered = []
        for e in entries:
            try:
                ts = datetime.fromisoformat(e.get("timestamp", "")).timestamp()
                if ts >= cutoff:
                    filtered.append(e)
            except (ValueError, TypeError):
                filtered.append(e)  # Include if can't parse date

        # Aggregate by source
        by_source = {}
        total = 0.0
        for e in filtered:
            src = e.get("source", "unknown")
            amt = e.get("amount", 0.0)
            by_source[src] = by_source.get(src, 0.0) + amt
            total += amt

        # Aggregate by payment method
        by_payment = {}
        for e in filtered:
            pm = e.get("payment_method", "unknown")
            amt = e.get("amount", 0.0)
            by_payment[pm] = by_payment.get(pm, 0.0) + amt

        return {
            "period_days": days,
            "total_revenue": round(total, 2),
            "transactions": len(filtered),
            "by_source": {k: round(v, 2) for k, v in sorted(by_source.items(), key=lambda x: -x[1])},
            "by_payment_method": {k: round(v, 2) for k, v in sorted(by_payment.items(), key=lambda x: -x[1])},
            "currency": "USD",
        }

    def usage_stats(self, days: int = 30) -> dict:
        """Get API usage statistics."""
        entries = self._load(USAGE_LOG)
        cutoff = time.time() - (days * 86400)

        filtered = []
        for e in entries:
            try:
                ts = datetime.fromisoformat(e.get("timestamp", "")).timestamp()
                if ts >= cutoff:
                    filtered.append(e)
            except (ValueError, TypeError):
                filtered.append(e)

        total_calls = len(filtered)
        total_tokens = sum(e.get("tokens_used", 0) for e in filtered)
        total_cost = sum(e.get("cost_estimate", 0.0) for e in filtered)

        by_endpoint = {}
        for e in filtered:
            ep = e.get("endpoint", "unknown")
            by_endpoint[ep] = by_endpoint.get(ep, 0) + 1

        return {
            "period_days": days,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_estimate": round(total_cost, 4),
            "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda x: -x[1])),
        }

    @staticmethod
    def _append(filepath: str, data: dict):
        """Append entry to JSONL."""
        try:
            with open(filepath, "a") as f:
                f.write(json.dumps(data, default=str) + "\n")
        except Exception as e:
            logger.error(f"Revenue log error: {e}")

    @staticmethod
    def _load(filepath: str) -> list[dict]:
        """Load all entries from JSONL."""
        if not os.path.exists(filepath):
            return []
        entries = []
        try:
            with open(filepath) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Revenue load error: {e}")
        return entries
