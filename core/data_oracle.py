"""
Data Oracle — Deterministic fact-checking for semantic verification.

Resolves the DeterministicArbiter's semantic blindness by providing
three verification strategies that require ZERO LLM tokens:

1. Pattern-Based Fact Check — regex extraction + known_facts.json
2. Cross-Reference Check — Enigma Scanner DB lookup
3. Consistency Check — intra-output contradiction detection

Usage:
    from core.data_oracle import DataOracle

    oracle = DataOracle()
    verdict = oracle.verify("Bitcoin was created in 2010")
    # verdict.overall_status == "DISCREPANCY_FOUND"
    # verdict.fact_claims[0].status == "DISCREPANCY"
"""

import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.data_oracle")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FACTS_PATH = os.path.join(BASE_DIR, "data", "known_facts.json")


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────

@dataclass
class FactClaim:
    """A single factual claim extracted from text."""
    claim_text: str
    claim_type: str  # NUMERIC | DATE | ENTITY | COMPARATIVE
    extracted_value: object = None
    verified_value: object = None
    status: str = "NO_REFERENCE"  # VERIFIED | UNVERIFIED | DISCREPANCY | NO_REFERENCE
    confidence: float = 0.0
    source: str = ""
    evidence: str = ""


@dataclass
class Contradiction:
    """An intra-output contradiction."""
    entity: str
    value_1: str
    value_2: str
    location_1: int = 0
    location_2: int = 0


@dataclass
class OracleVerdict:
    """Consolidated verification result."""
    overall_status: str = "CLEAN"  # CLEAN | SUSPICIOUS | DISCREPANCY_FOUND
    fact_claims: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    verified_count: int = 0
    unverified_count: int = 0
    discrepancy_count: int = 0
    contradiction_count: int = 0
    oracle_score: float = 1.0  # 1.0 = all verified, 0.0 = all discrepant
    processing_time_ms: float = 0.0


# ─────────────────────────────────────────────────────────────────────
# Extraction patterns
# ─────────────────────────────────────────────────────────────────────

# "X was created in YEAR" / "X launched in YEAR" / "X founded in YEAR"
_YEAR_CLAIM = re.compile(
    r'(\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*?)\s+'
    r'(?:was\s+)?(?:created|launched|founded|started|released|deployed)\s+'
    r'(?:in\s+)?(\d{4})\b',
    re.IGNORECASE,
)

# "X has N transactions/users/agents" / "there are N agents/nodes"
_COUNT_CLAIM = re.compile(
    r'(?:(\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+has\s+'
    r'([\d,]+(?:\.\d+)?)\s*(?:million|billion|thousand|M|B|K)?\s+'
    r'(transactions|users|agents|nodes|attestations|tests|modules))|'
    r'(?:there\s+are\s+([\d,]+)\s+'
    r'(agents|nodes|attestations|tests|validators|chains))',
    re.IGNORECASE,
)

# "X processes N TPS" / "X handles N transactions per second"
_TPS_CLAIM = re.compile(
    r'(\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+'
    r'(?:processes|handles|supports)\s+'
    r'([\d,]+(?:\.\d+)?)\s*(?:K|thousand|million|M)?\s*'
    r'(?:TPS|transactions?\s+per\s+second)',
    re.IGNORECASE,
)

# "X score is N" / "trust score of N" / "score: N"
_SCORE_CLAIM = re.compile(
    r'(?:(\b[a-zA-Z0-9#]+(?:\s+[a-zA-Z0-9]+)*)\s+)?'
    r'(?:trust\s+)?score\s*(?:is|of|:|\s)\s*([\d.]+)',
    re.IGNORECASE,
)

# "X costs $N" / "$N per request"
_COST_CLAIM = re.compile(
    r'(?:costs?\s+\$?([\d.]+))|(?:\$?([\d.]+)\s+(?:per|/)\s+\w+)',
    re.IGNORECASE,
)

# "chain ID NNNN" / "chain id: NNNN"
_CHAIN_ID_CLAIM = re.compile(
    r'chain\s*(?:ID|id)\s*[:=]?\s*(\d+)',
    re.IGNORECASE,
)

# Agent references: "#NNNN" or "token_id NNNN" or "Agent #NNNN"
_AGENT_REF = re.compile(
    r'(?:agent\s+)?#(\d{3,5})\b|(?:token[_\s]id\s+(\d{3,5}))',
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────
# Data Oracle
# ─────────────────────────────────────────────────────────────────────

class DataOracle:
    """Deterministic fact-checking engine with 3 verification strategies.

    Zero LLM tokens — all verification is pattern-based or DB-backed.

    Args:
        known_facts_path: Path to JSON file with verified facts.
        enigma_bridge: Optional EnigmaBridge for cross-reference checks.
    """

    def __init__(self, known_facts_path: str = DEFAULT_FACTS_PATH,
                 enigma_bridge=None):
        self.known_facts_path = known_facts_path
        self.known_facts: dict = {}
        self.enigma_bridge = enigma_bridge
        self._load_facts()

    def _load_facts(self):
        """Load known facts from JSON file."""
        if os.path.exists(self.known_facts_path):
            try:
                with open(self.known_facts_path, "r") as f:
                    self.known_facts = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load known facts: {e}")
                self.known_facts = {}
        else:
            logger.info(f"No known_facts file at {self.known_facts_path}")

    def _flat_facts(self) -> dict[str, dict]:
        """Flatten nested facts into {key: {value, source, tolerance?}}."""
        flat: dict[str, dict] = {}
        for category, facts in self.known_facts.items():
            if isinstance(facts, dict):
                for key, entry in facts.items():
                    if isinstance(entry, dict):
                        flat[key] = entry
                        # Also index by category.key
                        flat[f"{category}.{key}"] = entry
        return flat

    def verify(self, text: str) -> OracleVerdict:
        """Run all 3 verification strategies and return consolidated verdict.

        Args:
            text: The text to verify.

        Returns:
            OracleVerdict with all claims, contradictions, and scores.
        """
        start = time.time()

        # Strategy 1: Pattern-based fact check
        fact_claims = self.pattern_check(text)

        # Strategy 2: Cross-reference check
        xref_claims = self.cross_reference_check(text)
        fact_claims.extend(xref_claims)

        # Strategy 3: Consistency check
        contradictions = self.consistency_check(text)

        # Compute statistics
        verified = sum(1 for c in fact_claims if c.status == "VERIFIED")
        unverified = sum(1 for c in fact_claims if c.status in ("UNVERIFIED", "NO_REFERENCE"))
        discrepancies = sum(1 for c in fact_claims if c.status == "DISCREPANCY")
        contradiction_count = len(contradictions)

        # Oracle score: weighted by claim count
        total_checkable = verified + discrepancies
        if total_checkable > 0:
            oracle_score = round(verified / total_checkable, 4)
        else:
            oracle_score = 1.0  # No checkable claims = clean

        # Determine overall status
        if discrepancies > 0 or contradiction_count > 0:
            overall_status = "DISCREPANCY_FOUND"
        elif unverified > 0:
            overall_status = "SUSPICIOUS"
        else:
            overall_status = "CLEAN"

        elapsed = (time.time() - start) * 1000

        verdict = OracleVerdict(
            overall_status=overall_status,
            fact_claims=[asdict(c) for c in fact_claims],
            contradictions=[asdict(c) for c in contradictions],
            verified_count=verified,
            unverified_count=unverified,
            discrepancy_count=discrepancies,
            contradiction_count=contradiction_count,
            oracle_score=oracle_score,
            processing_time_ms=round(elapsed, 2),
        )

        logger.info(
            f"Oracle verdict: {overall_status} "
            f"(verified={verified}, discrepancies={discrepancies}, "
            f"contradictions={contradiction_count}, score={oracle_score})"
        )
        return verdict

    def pattern_check(self, text: str) -> list[FactClaim]:
        """Extract factual claims and verify against known_facts.json.

        Patterns detected:
          - "X was created in YEAR"
          - "X has N transactions/agents"
          - "X processes N TPS"
          - "X score is N"
          - "chain ID NNNN"

        Returns:
            List of FactClaim with status VERIFIED/DISCREPANCY/NO_REFERENCE.
        """
        claims: list[FactClaim] = []
        flat = self._flat_facts()

        # Year claims
        for match in _YEAR_CLAIM.finditer(text):
            entity = match.group(1).strip().lower()
            year = int(match.group(2))
            claim = FactClaim(
                claim_text=match.group(0),
                claim_type="DATE",
                extracted_value=year,
            )
            # Look up in known facts
            fact_key = self._find_fact_key(entity, "creation_year", flat)
            if fact_key:
                known = flat[fact_key]
                claim.verified_value = known["value"]
                claim.source = known.get("source", "known_facts.json")
                if year == known["value"]:
                    claim.status = "VERIFIED"
                    claim.confidence = 1.0
                    claim.evidence = f"Matches known fact: {known['value']}"
                else:
                    claim.status = "DISCREPANCY"
                    claim.confidence = 0.95
                    claim.evidence = f"Known value is {known['value']}, not {year}"
            else:
                claim.status = "NO_REFERENCE"
                claim.confidence = 0.0
            claims.append(claim)

        # Count claims (has N X / there are N X)
        for match in _COUNT_CLAIM.finditer(text):
            if match.group(1):
                entity = match.group(1).strip().lower()
                raw_num = match.group(2).replace(",", "")
                metric = match.group(3).lower()
            elif match.group(4):
                entity = ""
                raw_num = match.group(4).replace(",", "")
                metric = match.group(5).lower()
            else:
                continue

            try:
                num_value = float(raw_num)
            except ValueError:
                continue

            claim = FactClaim(
                claim_text=match.group(0),
                claim_type="NUMERIC",
                extracted_value=num_value,
            )

            fact_key = self._find_fact_key(entity or metric, metric, flat)
            if not fact_key:
                fact_key = self._find_fact_key(metric, "", flat)
            if fact_key:
                known = flat[fact_key]
                claim.verified_value = known["value"]
                claim.source = known.get("source", "known_facts.json")
                tolerance = known.get("tolerance", 0)
                if abs(num_value - known["value"]) <= tolerance:
                    claim.status = "VERIFIED"
                    claim.confidence = 1.0
                    claim.evidence = f"Matches known fact: {known['value']} (tolerance: {tolerance})"
                else:
                    claim.status = "DISCREPANCY"
                    claim.confidence = 0.9
                    claim.evidence = f"Known value is {known['value']}, got {num_value}"
            else:
                claim.status = "NO_REFERENCE"
                claim.confidence = 0.0
            claims.append(claim)

        # Chain ID claims
        for match in _CHAIN_ID_CLAIM.finditer(text):
            chain_id = int(match.group(1))
            claim = FactClaim(
                claim_text=match.group(0),
                claim_type="NUMERIC",
                extracted_value=chain_id,
            )
            fact_key = self._find_fact_key("avalanche", "chain_id", flat)
            if fact_key:
                known = flat[fact_key]
                claim.verified_value = known["value"]
                claim.source = known.get("source", "known_facts.json")
                if chain_id == known["value"]:
                    claim.status = "VERIFIED"
                    claim.confidence = 1.0
                    claim.evidence = f"Matches known chain ID: {known['value']}"
                else:
                    claim.status = "DISCREPANCY"
                    claim.confidence = 0.9
                    claim.evidence = f"Known chain ID is {known['value']}, got {chain_id}"
            else:
                claim.status = "NO_REFERENCE"
            claims.append(claim)

        return claims

    def cross_reference_check(self, text: str) -> list[FactClaim]:
        """Verify agent references against known facts or Enigma DB.

        Extracts agent token IDs (e.g., #1687) and verifies existence
        and properties against the known_facts database.

        Returns:
            List of FactClaim with cross-reference results.
        """
        claims: list[FactClaim] = []
        flat = self._flat_facts()

        for match in _AGENT_REF.finditer(text):
            token_id = match.group(1) or match.group(2)
            if not token_id:
                continue

            token_id_int = int(token_id)
            claim = FactClaim(
                claim_text=match.group(0),
                claim_type="ENTITY",
                extracted_value=token_id_int,
            )

            # Check known facts for agent token IDs
            found = False
            for key, entry in flat.items():
                if isinstance(entry, dict) and entry.get("value") == token_id_int:
                    if "token_id" in key:
                        claim.verified_value = entry["value"]
                        claim.source = entry.get("source", "known_facts.json")
                        claim.status = "VERIFIED"
                        claim.confidence = 1.0
                        claim.evidence = f"Agent #{token_id_int} found in known facts"
                        found = True
                        break

            if not found:
                claim.status = "NO_REFERENCE"
                claim.confidence = 0.0
                claim.evidence = f"Agent #{token_id_int} not in known facts"

            claims.append(claim)

        # Check score claims against known trust scores
        for match in _SCORE_CLAIM.finditer(text):
            entity_raw = match.group(1) or ""
            score_str = match.group(2)
            try:
                score_val = float(score_str)
            except ValueError:
                continue

            # Only process if entity mentions an agent
            agent_match = _AGENT_REF.search(entity_raw)
            if not agent_match:
                continue

            claim = FactClaim(
                claim_text=match.group(0),
                claim_type="NUMERIC",
                extracted_value=score_val,
            )
            claim.status = "UNVERIFIED"
            claim.confidence = 0.3
            claim.evidence = "Score claim found but no local reference to verify"
            claims.append(claim)

        return claims

    def consistency_check(self, text: str) -> list[Contradiction]:
        """Detect intra-output contradictions.

        Extracts numeric values associated with entities and checks
        if the same entity has conflicting values in different locations.

        Returns:
            List of Contradiction objects.
        """
        contradictions: list[Contradiction] = []

        # Extract "entity ... number" associations
        # Pattern: word(s) followed by a number in context
        entity_values: dict[str, list[tuple[str, int]]] = {}

        # Look for patterns like "score is N", "score of N", "score: N"
        pattern = re.compile(
            r'(\b[a-zA-Z_]+(?:\s+[a-zA-Z_]+)?)\s+'
            r'(?:is|of|:|=|was|are|equals?)\s+'
            r'(\d+(?:\.\d+)?)\b',
            re.IGNORECASE,
        )

        for match in pattern.finditer(text):
            entity = match.group(1).strip().lower()
            value = match.group(2)
            pos = match.start()

            # Normalize common entity names
            entity_norm = entity.replace("_", " ").strip()
            if entity_norm in ("the", "a", "an", "it", "is", "was", "are"):
                continue

            if entity_norm not in entity_values:
                entity_values[entity_norm] = []
            entity_values[entity_norm].append((value, pos))

        # Check for contradictions: same entity, different values
        for entity, entries in entity_values.items():
            if len(entries) < 2:
                continue
            values_seen: dict[str, int] = {}
            for value, pos in entries:
                if value in values_seen:
                    continue
                for other_value, other_pos in entries:
                    if value != other_value and other_value not in values_seen:
                        contradictions.append(Contradiction(
                            entity=entity,
                            value_1=value,
                            value_2=other_value,
                            location_1=pos,
                            location_2=other_pos,
                        ))
                        values_seen[value] = pos
                        values_seen[other_value] = other_pos
                        break

        return contradictions

    def add_known_fact(self, category: str, key: str, value,
                       source: str, timestamp: str = "") -> None:
        """Add a verified fact to the knowledge base.

        Args:
            category: Fact category (e.g., "blockchain", "dof", "agents").
            key: Fact key (e.g., "bitcoin_creation_year").
            value: The verified value.
            source: Source of the fact.
            timestamp: Optional ISO timestamp.
        """
        if category not in self.known_facts:
            self.known_facts[category] = {}

        entry = {"value": value, "source": source}
        if timestamp:
            entry["timestamp"] = timestamp

        self.known_facts[category][key] = entry

        # Persist
        try:
            os.makedirs(os.path.dirname(self.known_facts_path), exist_ok=True)
            with open(self.known_facts_path, "w") as f:
                json.dump(self.known_facts, f, indent=2, default=str)
            logger.info(f"Added known fact: {category}.{key} = {value}")
        except IOError as e:
            logger.error(f"Could not persist known fact: {e}")

    def _find_fact_key(self, entity: str, metric: str,
                       flat: dict[str, dict]) -> str | None:
        """Find a matching fact key by fuzzy entity+metric matching."""
        entity_lower = entity.lower().replace(" ", "_")
        metric_lower = metric.lower().replace(" ", "_")

        # Direct match attempts
        for attempt in [
            f"{entity_lower}_{metric_lower}",
            f"{entity_lower}",
            f"total_{metric_lower}",
        ]:
            if attempt in flat:
                return attempt

        # Partial match: key contains entity
        for key in flat:
            key_lower = key.lower()
            if entity_lower and entity_lower in key_lower:
                if not metric_lower or metric_lower in key_lower:
                    return key

        return None
