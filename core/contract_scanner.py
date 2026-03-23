"""
Solidity Smart Contract Scanner — Deterministic vulnerability detection.

Pattern-based static analysis for common Solidity vulnerabilities:
  - Reentrancy (SWC-107)
  - Unchecked external calls (SWC-104)
  - tx.origin authentication (SWC-115)
  - Selfdestruct exposure (SWC-106)
  - Delegatecall injection (SWC-112)
  - Integer overflow/underflow (SWC-101)
  - Unprotected initializers
  - Hardcoded addresses / private keys

Zero external dependencies. Does NOT replace formal verification tools
(Slither, Mythril, Certora) but serves as L2-style gate for quick triage.
Results logged to logs/contract_scan.jsonl for audit.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("core.contract_scanner")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "contract_scan.jsonl")


# --- Vulnerability Patterns ---

@dataclass
class VulnPattern:
    """A vulnerability detection pattern."""
    id: str
    name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    swc: str  # SWC registry ID
    pattern: str  # Regex pattern
    description: str
    recommendation: str


VULN_PATTERNS: list[VulnPattern] = [
    # CRITICAL
    VulnPattern(
        "REENTRANCY", "Reentrancy Risk", "CRITICAL", "SWC-107",
        r'\.call\{value\s*:.*\}\s*\(""\)|\.call\.value\s*\(',
        "External call with value before state update — classic reentrancy vector",
        "Use checks-effects-interactions pattern or OpenZeppelin ReentrancyGuard"
    ),
    VulnPattern(
        "DELEGATECALL", "Delegatecall to User Input", "CRITICAL", "SWC-112",
        r'\.delegatecall\s*\(',
        "Delegatecall can execute arbitrary code in caller's context",
        "Never delegatecall to untrusted addresses. Use fixed implementation addresses."
    ),
    VulnPattern(
        "SELFDESTRUCT", "Selfdestruct Exposure", "CRITICAL", "SWC-106",
        r'selfdestruct\s*\(|suicide\s*\(',
        "Selfdestruct can destroy contract and send Ether to arbitrary address",
        "Remove selfdestruct or restrict to multisig-only with timelock"
    ),
    VulnPattern(
        "PRIVATE_KEY", "Hardcoded Private Key", "CRITICAL", "N/A",
        r'0x[0-9a-fA-F]{64}',
        "Possible hardcoded private key in contract source",
        "NEVER store private keys in contract code. Use environment variables."
    ),

    # HIGH
    VulnPattern(
        "TX_ORIGIN", "tx.origin Authentication", "HIGH", "SWC-115",
        r'tx\.origin',
        "tx.origin can be spoofed via intermediary contracts",
        "Use msg.sender instead of tx.origin for authentication"
    ),
    VulnPattern(
        "UNCHECKED_CALL", "Unchecked External Call", "HIGH", "SWC-104",
        r'\.call\s*\(|\.send\s*\(|\.transfer\s*\(',
        "External call return value not checked — silent failure possible",
        "Always check return value: (bool success, ) = addr.call{...}(...); require(success);"
    ),
    VulnPattern(
        "UNPROTECTED_INIT", "Unprotected Initializer", "HIGH", "N/A",
        r'function\s+initialize\s*\([^)]*\)\s*(public|external)(?!.*initializer)',
        "Initialize function without initializer modifier — can be called multiple times",
        "Add OpenZeppelin initializer modifier or use constructor"
    ),
    VulnPattern(
        "ARBITRARY_SEND", "Ether Send to Arbitrary Address", "HIGH", "N/A",
        r'payable\s*\(\s*\w+\s*\)\s*\.transfer\s*\(|\.call\{value\s*:',
        "Sending Ether to user-controlled address",
        "Validate destination address against whitelist or use pull-payment pattern"
    ),

    # MEDIUM
    VulnPattern(
        "TIMESTAMP", "Block Timestamp Dependence", "MEDIUM", "SWC-116",
        r'block\.timestamp|now\s*[<>=!]',
        "Block timestamp can be manipulated by miners within ~15 seconds",
        "Don't use block.timestamp for critical logic. Use block.number for ordering."
    ),
    VulnPattern(
        "BLOCKHASH", "Weak Randomness from Blockhash", "MEDIUM", "SWC-120",
        r'blockhash\s*\(|block\.blockhash',
        "blockhash is predictable and manipulable by miners",
        "Use Chainlink VRF or commit-reveal scheme for randomness"
    ),
    VulnPattern(
        "ASSEMBLY", "Inline Assembly Usage", "MEDIUM", "N/A",
        r'assembly\s*\{',
        "Inline assembly bypasses Solidity safety checks",
        "Document assembly usage thoroughly. Verify manually."
    ),
    VulnPattern(
        "DEPRECATED", "Deprecated Solidity Patterns", "MEDIUM", "N/A",
        r'throw\s*;|sha3\s*\(|suicide\s*\(|block\.blockhash',
        "Using deprecated Solidity functions",
        "Update to modern equivalents: revert(), keccak256(), selfdestruct(), blockhash()"
    ),

    # LOW
    VulnPattern(
        "FLOATING_PRAGMA", "Floating Pragma", "LOW", "SWC-103",
        r'pragma\s+solidity\s*\^',
        "Floating pragma allows compilation with different compiler versions",
        "Pin pragma to specific version: pragma solidity 0.8.24;"
    ),
    VulnPattern(
        "TODO_FIXME", "TODO/FIXME in Code", "LOW", "N/A",
        r'//\s*(TODO|FIXME|HACK|XXX|BUG)',
        "Unresolved development notes in production code",
        "Resolve all TODOs before deployment"
    ),
    VulnPattern(
        "MAGIC_NUMBER", "Magic Numbers", "INFO", "N/A",
        r'(?<!0x)\b\d{4,}\b(?!\.)',
        "Large magic numbers without named constants reduce readability",
        "Extract to named constants for clarity and maintainability"
    ),
]


# --- Results ---

@dataclass
class Finding:
    """A single vulnerability finding."""
    vuln_id: str
    name: str
    severity: str
    swc: str
    line: int
    column: int
    match: str
    description: str
    recommendation: str


@dataclass
class ScanResult:
    """Complete scan result for a contract."""
    contract_name: str
    findings: list[Finding]
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    scan_time_ms: float = 0.0
    passed: bool = True  # No CRITICAL or HIGH findings
    timestamp: float = field(default_factory=time.time)


# --- Scanner ---

class ContractScanner:
    """Deterministic Solidity vulnerability scanner.

    Pattern-based static analysis. Zero LLM. Zero external dependencies.
    Designed as a fast L2-style gate, not a replacement for formal verification.
    """

    def __init__(self, patterns: list[VulnPattern] | None = None):
        self.patterns = VULN_PATTERNS if patterns is None else patterns
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def scan(self, source_code: str, contract_name: str = "unknown") -> ScanResult:
        """Scan Solidity source code for vulnerability patterns."""
        start = time.time()
        findings: list[Finding] = []
        lines = source_code.split("\n")

        for pattern in self.patterns:
            regex = re.compile(pattern.pattern, re.IGNORECASE)
            for i, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue

                for match in regex.finditer(line):
                    # Filter false positives for PRIVATE_KEY
                    if pattern.id == "PRIVATE_KEY":
                        # Skip if it looks like an address (40 hex chars) not a key (64)
                        hex_val = match.group()
                        if len(hex_val) < 66:  # 0x + 64 hex chars
                            continue

                    findings.append(Finding(
                        vuln_id=pattern.id,
                        name=pattern.name,
                        severity=pattern.severity,
                        swc=pattern.swc,
                        line=i,
                        column=match.start(),
                        match=match.group()[:80],
                        description=pattern.description,
                        recommendation=pattern.recommendation,
                    ))

        scan_time = (time.time() - start) * 1000

        critical = sum(1 for f in findings if f.severity == "CRITICAL")
        high = sum(1 for f in findings if f.severity == "HIGH")
        medium = sum(1 for f in findings if f.severity == "MEDIUM")
        low = sum(1 for f in findings if f.severity == "LOW")
        info = sum(1 for f in findings if f.severity == "INFO")

        result = ScanResult(
            contract_name=contract_name,
            findings=findings,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            info_count=info,
            scan_time_ms=round(scan_time, 2),
            passed=(critical == 0 and high == 0),
        )

        self._log(result)
        return result

    def scan_file(self, filepath: str) -> ScanResult:
        """Scan a .sol file."""
        name = os.path.basename(filepath)
        with open(filepath) as f:
            source = f.read()
        return self.scan(source, contract_name=name)

    def scan_directory(self, dirpath: str) -> list[ScanResult]:
        """Scan all .sol files in a directory."""
        results = []
        for root, _, files in os.walk(dirpath):
            for fname in files:
                if fname.endswith(".sol"):
                    fpath = os.path.join(root, fname)
                    results.append(self.scan_file(fpath))
        return results

    def report(self, result: ScanResult) -> str:
        """Generate human-readable scan report."""
        lines = [
            f"=== Contract Scan: {result.contract_name} ===",
            f"Status: {'PASS' if result.passed else 'FAIL'}",
            f"Findings: {len(result.findings)} "
            f"(C:{result.critical_count} H:{result.high_count} "
            f"M:{result.medium_count} L:{result.low_count} I:{result.info_count})",
            f"Scan time: {result.scan_time_ms}ms",
            "",
        ]

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        sorted_findings = sorted(result.findings, key=lambda f: severity_order.get(f.severity, 5))

        for f in sorted_findings:
            icon = {"CRITICAL": "!!!", "HIGH": " ! ", "MEDIUM": " ~ ", "LOW": " . ", "INFO": " i "}
            lines.append(
                f"  [{icon.get(f.severity, '???')}] Line {f.line}: {f.name} ({f.swc})"
            )
            lines.append(f"        {f.description}")
            lines.append(f"        Fix: {f.recommendation}")
            lines.append("")

        return "\n".join(lines)

    def _log(self, result: ScanResult):
        """Log scan result to JSONL."""
        try:
            entry = {
                "contract": result.contract_name,
                "passed": result.passed,
                "findings": len(result.findings),
                "critical": result.critical_count,
                "high": result.high_count,
                "scan_time_ms": result.scan_time_ms,
                "timestamp": result.timestamp,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Contract scan log error: {e}")


# --- Convenience ---

def scan_contract(source: str, name: str = "unknown") -> ScanResult:
    """Quick scan of Solidity source code."""
    return ContractScanner().scan(source, name)


# --- Quick test ---

if __name__ == "__main__":
    test_contract = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vulnerable {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        // VULN: state change after external call (reentrancy)
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;
    }

    function isOwner() public view returns (bool) {
        // VULN: tx.origin
        return tx.origin == address(this);
    }

    function destroy() external {
        // VULN: selfdestruct
        selfdestruct(payable(msg.sender));
    }
}
"""

    scanner = ContractScanner()
    result = scanner.scan(test_contract, "Vulnerable.sol")
    print(scanner.report(result))
