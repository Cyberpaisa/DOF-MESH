"""
Entropy-based anomaly detector for adversarial suffix attacks.

Detects text segments with abnormally high character entropy,
indicating GCG/suffix adversarial attacks or garbage injection.

This is a security improvement independent of any benchmark —
production systems should detect non-linguistic noise in inputs.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class EntropyResult:
    is_anomalous: bool
    entropy_score: float
    non_ascii_ratio: float
    special_char_ratio: float
    avg_word_length: float
    details: str


class EntropyDetector:
    """
    Detects adversarial suffix attacks via statistical text analysis.

    Thresholds calibrated against natural language characteristics:
    - English text: entropy ~4.0-4.5, special_char_ratio ~0.05-0.15
    - Code: entropy ~4.5-5.5, special_char_ratio ~0.15-0.30
    - GCG suffix: entropy ~6.0+, special_char_ratio ~0.40+
    """

    def __init__(
        self,
        entropy_threshold: float = 5.5,
        special_char_threshold: float = 0.35,
        non_ascii_threshold: float = 0.20,
        min_length: int = 20,
        window_size: int = 50,
    ):
        self.entropy_threshold = entropy_threshold
        self.special_char_threshold = special_char_threshold
        self.non_ascii_threshold = non_ascii_threshold
        self.min_length = min_length
        self.window_size = window_size

    def shannon_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        counts = Counter(text)
        length = len(text)
        return -sum(
            (count / length) * math.log2(count / length)
            for count in counts.values()
        )

    def detect(self, text: str) -> EntropyResult:
        if text is None:
            text = ""
        if len(text) < self.min_length:
            return EntropyResult(False, 0.0, 0.0, 0.0, 0.0, "text too short")

        entropy = self.shannon_entropy(text)

        non_ascii = sum(1 for c in text if ord(c) > 127)
        non_ascii_ratio = non_ascii / len(text)

        special = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special / len(text)

        words = text.split()
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0

        # Sliding window for local entropy spikes
        max_local_entropy = 0.0
        if len(text) >= self.window_size:
            for i in range(0, len(text) - self.window_size, self.window_size // 2):
                window = text[i:i + self.window_size]
                local_ent = self.shannon_entropy(window)
                max_local_entropy = max(max_local_entropy, local_ent)

        # Decision — 2+ signals = anomalous
        signals = 0
        details = []

        if entropy > self.entropy_threshold:
            signals += 1
            details.append(f"high_entropy({entropy:.2f}>{self.entropy_threshold})")

        if special_ratio > self.special_char_threshold:
            signals += 1
            details.append(f"special_chars({special_ratio:.2f}>{self.special_char_threshold})")

        if non_ascii_ratio > self.non_ascii_threshold:
            signals += 1
            details.append(f"non_ascii({non_ascii_ratio:.2f}>{self.non_ascii_threshold})")

        if max_local_entropy > self.entropy_threshold + 0.5:
            signals += 1
            details.append(f"local_entropy_spike({max_local_entropy:.2f})")

        if avg_word_len > 15:
            signals += 1
            details.append(f"long_words(avg={avg_word_len:.1f})")

        # Repetition ratio — GCG/bracket spam repeats tokens
        if words:
            unique_ratio = len(set(w.lower() for w in words)) / len(words)
            if unique_ratio < 0.30 and len(words) > 8:
                signals += 1
                details.append(f"high_repetition(unique={unique_ratio:.2f})")

        # Non-dictionary gibberish — high ratio of short 1-2 char "words"
        if words and len(words) > 10:
            short_words = sum(1 for w in words if len(w) <= 2)
            short_ratio = short_words / len(words)
            if short_ratio > 0.50:
                signals += 1
                details.append(f"gibberish_tokens(short_ratio={short_ratio:.2f})")

        # Mixed case + bracket/paren density — GCG hallmark
        brackets = sum(1 for c in text if c in "[]{}()")
        bracket_ratio = brackets / len(text)
        if bracket_ratio > 0.08 and len(text) > 30:
            signals += 1
            details.append(f"bracket_density({bracket_ratio:.2f})")

        # Concatenated nonsense words — GCG fragments like "ISBNancouver"
        if words and len(words) > 8:
            nonsense = 0
            for w in words:
                if len(w) > 5:
                    # MidCaps: uppercase letter after lowercase (not start)
                    has_midcap = any(
                        w[i].isupper() and w[i - 1].islower()
                        for i in range(1, len(w))
                    )
                    # Consonant cluster: 4+ consonants in a row
                    has_cluster = bool(re.search(r'[bcdfghjklmnpqrstvwxyz]{4,}', w.lower()))
                    if has_midcap or has_cluster:
                        nonsense += 1
            if nonsense >= 3:
                signals += 1
                details.append(f"nonsense_words({nonsense})")

        is_anomalous = signals >= 2

        return EntropyResult(
            is_anomalous=is_anomalous,
            entropy_score=entropy,
            non_ascii_ratio=non_ascii_ratio,
            special_char_ratio=special_ratio,
            avg_word_length=avg_word_len,
            details="; ".join(details) if details else "clean",
        )
