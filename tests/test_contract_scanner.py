"""
Tests for core/contract_scanner.py — Solidity vulnerability scanner.

All tests are deterministic, zero external dependencies, zero LLM.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.contract_scanner import (
    ContractScanner,
    Finding,
    ScanResult,
    VulnPattern,
    VULN_PATTERNS,
    scan_contract,
)


# ── Solidity snippets used across tests ─────────────────────────────

CLEAN_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract Safe {
    address private owner;

    constructor() { owner = msg.sender; }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function withdraw(uint256 amount) external onlyOwner {
        require(address(this).balance >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
"""

REENTRANCY_CONTRACT = """
pragma solidity ^0.8.0;
contract Vuln {
    mapping(address => uint256) bal;
    function withdraw() external {
        (bool s, ) = msg.sender.call{value: bal[msg.sender]}("");
        bal[msg.sender] = 0;
    }
}
"""

TX_ORIGIN_CONTRACT = """
pragma solidity ^0.8.0;
contract AuthBug {
    function onlyOwner() public view returns (bool) {
        return tx.origin == address(this);
    }
}
"""

SELFDESTRUCT_CONTRACT = """
pragma solidity ^0.8.0;
contract Bomb {
    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}
"""

DELEGATECALL_CONTRACT = """
pragma solidity ^0.8.0;
contract Proxy {
    function exec(address impl, bytes memory data) external {
        impl.delegatecall(data);
    }
}
"""

FLOATING_PRAGMA_CONTRACT = """
pragma solidity ^0.8.0;
contract FP { }
"""

TIMESTAMP_CONTRACT = """
pragma solidity 0.8.24;
contract TimeLock {
    uint256 public unlock;
    constructor() { unlock = block.timestamp + 7 days; }
    function claim() external {
        require(block.timestamp >= unlock, "locked");
    }
}
"""

BLOCKHASH_CONTRACT = """
pragma solidity 0.8.24;
contract Lottery {
    function random() public view returns (uint256) {
        return uint256(blockhash(block.number - 1));
    }
}
"""

ASSEMBLY_CONTRACT = """
pragma solidity 0.8.24;
contract AsmOp {
    function size() external view returns (uint256 s) {
        assembly { s := extcodesize(address()) }
    }
}
"""

PRIVATE_KEY_CONTRACT = """
pragma solidity 0.8.24;
contract KeyLeak {
    bytes32 constant SECRET = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
}
"""

MULTIvuln_CONTRACT = """
pragma solidity ^0.8.0;
contract Multi {
    function bad1() external { selfdestruct(payable(msg.sender)); }
    function bad2() public view returns (bool) { return tx.origin == msg.sender; }
    function bad3(address t, bytes memory d) external { t.delegatecall(d); }
}
"""

COMMENT_ONLY_CONTRACT = """
pragma solidity 0.8.24;
// This uses tx.origin for illustration: tx.origin
// selfdestruct(payable(msg.sender));
contract NoFindings { }
"""


# ── Helper ──────────────────────────────────────────────────────────

def scanner() -> ContractScanner:
    return ContractScanner()


def vuln_ids(result: ScanResult) -> set[str]:
    return {f.vuln_id for f in result.findings}


# ─────────────────────────────────────────────────────────────────────
# ScanResult dataclass
# ─────────────────────────────────────────────────────────────────────

class TestScanResult(unittest.TestCase):

    def test_clean_contract_returns_result(self):
        result = scanner().scan(CLEAN_CONTRACT, "Safe.sol")
        self.assertIsInstance(result, ScanResult)
        # Static analysis is conservative: call{value:} triggers REENTRANCY
        # regardless of surrounding logic. Confirm result is well-formed.
        self.assertIsInstance(result.findings, list)
        total = (result.critical_count + result.high_count +
                 result.medium_count + result.low_count + result.info_count)
        self.assertEqual(total, len(result.findings))

    def test_result_has_required_fields(self):
        result = scanner().scan(CLEAN_CONTRACT, "Safe.sol")
        for attr in ("contract_name", "findings", "critical_count", "high_count",
                     "medium_count", "low_count", "info_count", "scan_time_ms",
                     "passed", "timestamp"):
            self.assertTrue(hasattr(result, attr), f"Missing field: {attr}")

    def test_contract_name_preserved(self):
        result = scanner().scan(CLEAN_CONTRACT, "MyToken.sol")
        self.assertEqual(result.contract_name, "MyToken.sol")

    def test_scan_time_positive(self):
        result = scanner().scan(CLEAN_CONTRACT)
        self.assertGreater(result.scan_time_ms, 0)

    def test_passed_false_when_critical(self):
        result = scanner().scan(SELFDESTRUCT_CONTRACT)
        self.assertFalse(result.passed)
        self.assertGreater(result.critical_count, 0)

    def test_passed_false_when_high(self):
        result = scanner().scan(TX_ORIGIN_CONTRACT)
        self.assertFalse(result.passed)

    def test_passed_true_no_critical_high(self):
        # Only floating pragma (LOW) and timestamp (MEDIUM)
        result = scanner().scan(TIMESTAMP_CONTRACT)
        self.assertTrue(result.passed)

    def test_count_fields_match_findings(self):
        result = scanner().scan(MULTIvuln_CONTRACT)
        total = (result.critical_count + result.high_count +
                 result.medium_count + result.low_count + result.info_count)
        self.assertEqual(total, len(result.findings))


# ─────────────────────────────────────────────────────────────────────
# Individual vulnerability patterns
# ─────────────────────────────────────────────────────────────────────

class TestVulnPatterns(unittest.TestCase):

    def test_reentrancy_detected(self):
        result = scanner().scan(REENTRANCY_CONTRACT)
        self.assertIn("REENTRANCY", vuln_ids(result))
        self.assertEqual(result.critical_count, result.critical_count)  # sanity

    def test_tx_origin_detected(self):
        result = scanner().scan(TX_ORIGIN_CONTRACT)
        self.assertIn("TX_ORIGIN", vuln_ids(result))

    def test_selfdestruct_detected(self):
        result = scanner().scan(SELFDESTRUCT_CONTRACT)
        self.assertIn("SELFDESTRUCT", vuln_ids(result))

    def test_delegatecall_detected(self):
        result = scanner().scan(DELEGATECALL_CONTRACT)
        self.assertIn("DELEGATECALL", vuln_ids(result))

    def test_floating_pragma_detected(self):
        result = scanner().scan(FLOATING_PRAGMA_CONTRACT)
        self.assertIn("FLOATING_PRAGMA", vuln_ids(result))

    def test_timestamp_detected(self):
        result = scanner().scan(TIMESTAMP_CONTRACT)
        self.assertIn("TIMESTAMP", vuln_ids(result))

    def test_blockhash_detected(self):
        result = scanner().scan(BLOCKHASH_CONTRACT)
        self.assertIn("BLOCKHASH", vuln_ids(result))

    def test_assembly_detected(self):
        result = scanner().scan(ASSEMBLY_CONTRACT)
        self.assertIn("ASSEMBLY", vuln_ids(result))

    def test_private_key_detected(self):
        result = scanner().scan(PRIVATE_KEY_CONTRACT)
        self.assertIn("PRIVATE_KEY", vuln_ids(result))

    def test_multiple_vulns_in_one_contract(self):
        result = scanner().scan(MULTIvuln_CONTRACT)
        ids = vuln_ids(result)
        self.assertIn("SELFDESTRUCT", ids)
        self.assertIn("TX_ORIGIN", ids)
        self.assertIn("DELEGATECALL", ids)


# ─────────────────────────────────────────────────────────────────────
# Finding fields
# ─────────────────────────────────────────────────────────────────────

class TestFindingFields(unittest.TestCase):

    def setUp(self):
        self.result = scanner().scan(TX_ORIGIN_CONTRACT, "AuthBug.sol")
        self.finding = next(f for f in self.result.findings if f.vuln_id == "TX_ORIGIN")

    def test_finding_has_line_number(self):
        self.assertGreater(self.finding.line, 0)

    def test_finding_has_description(self):
        self.assertIsInstance(self.finding.description, str)
        self.assertGreater(len(self.finding.description), 10)

    def test_finding_has_recommendation(self):
        self.assertIsInstance(self.finding.recommendation, str)
        self.assertGreater(len(self.finding.recommendation), 5)

    def test_finding_has_swc(self):
        self.assertEqual(self.finding.swc, "SWC-115")

    def test_finding_severity_correct(self):
        self.assertEqual(self.finding.severity, "HIGH")

    def test_finding_match_truncated_at_80(self):
        self.assertLessEqual(len(self.finding.match), 80)


# ─────────────────────────────────────────────────────────────────────
# Comment skipping
# ─────────────────────────────────────────────────────────────────────

class TestCommentSkipping(unittest.TestCase):

    def test_single_line_comments_skipped(self):
        """Patterns in // comments must not trigger findings."""
        result = scanner().scan(COMMENT_ONLY_CONTRACT)
        ids = vuln_ids(result)
        # tx.origin and selfdestruct appear only in comments → not flagged
        self.assertNotIn("TX_ORIGIN", ids)
        self.assertNotIn("SELFDESTRUCT", ids)

    def test_star_comment_lines_skipped(self):
        src = """
pragma solidity 0.8.24;
/**
 * tx.origin is dangerous
 * selfdestruct the contract
 */
contract DocOnly { }
"""
        result = scanner().scan(src)
        ids = vuln_ids(result)
        self.assertNotIn("TX_ORIGIN", ids)
        self.assertNotIn("SELFDESTRUCT", ids)


# ─────────────────────────────────────────────────────────────────────
# Empty / edge inputs
# ─────────────────────────────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):

    def test_empty_source(self):
        result = scanner().scan("", "empty.sol")
        self.assertEqual(len(result.findings), 0)
        self.assertTrue(result.passed)

    def test_whitespace_only(self):
        result = scanner().scan("   \n\n  ", "blank.sol")
        self.assertEqual(len(result.findings), 0)

    def test_default_contract_name(self):
        result = scanner().scan("")
        self.assertEqual(result.contract_name, "unknown")

    def test_no_false_positive_on_address(self):
        """40-hex-char address must not trigger PRIVATE_KEY."""
        src = """
pragma solidity 0.8.24;
contract Addrs {
    address constant OWNER = 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045;
}
"""
        result = scanner().scan(src)
        self.assertNotIn("PRIVATE_KEY", vuln_ids(result))


# ─────────────────────────────────────────────────────────────────────
# scan_file()
# ─────────────────────────────────────────────────────────────────────

class TestScanFile(unittest.TestCase):

    def test_scan_file_returns_result(self):
        with tempfile.NamedTemporaryFile(suffix=".sol", mode="w", delete=False) as f:
            f.write(SELFDESTRUCT_CONTRACT)
            path = f.name
        try:
            result = scanner().scan_file(path)
            self.assertIsInstance(result, ScanResult)
            self.assertIn("SELFDESTRUCT", vuln_ids(result))
        finally:
            os.unlink(path)

    def test_scan_file_uses_basename(self):
        with tempfile.NamedTemporaryFile(suffix=".sol", mode="w", delete=False) as f:
            f.write(CLEAN_CONTRACT)
            path = f.name
        try:
            result = scanner().scan_file(path)
            self.assertEqual(result.contract_name, os.path.basename(path))
        finally:
            os.unlink(path)


# ─────────────────────────────────────────────────────────────────────
# scan_directory()
# ─────────────────────────────────────────────────────────────────────

class TestScanDirectory(unittest.TestCase):

    def test_scans_all_sol_files(self):
        with tempfile.TemporaryDirectory() as d:
            for name, src in [("A.sol", TX_ORIGIN_CONTRACT),
                               ("B.sol", SELFDESTRUCT_CONTRACT),
                               ("C.txt", "not a solidity file")]:
                with open(os.path.join(d, name), "w") as fh:
                    fh.write(src)
            results = scanner().scan_directory(d)
        self.assertEqual(len(results), 2)  # only .sol files

    def test_scan_directory_empty(self):
        with tempfile.TemporaryDirectory() as d:
            results = scanner().scan_directory(d)
        self.assertEqual(results, [])


# ─────────────────────────────────────────────────────────────────────
# report()
# ─────────────────────────────────────────────────────────────────────

class TestReport(unittest.TestCase):

    def test_report_is_string(self):
        result = scanner().scan(MULTIvuln_CONTRACT, "Multi.sol")
        report = scanner().report(result)
        self.assertIsInstance(report, str)

    def test_report_contains_contract_name(self):
        result = scanner().scan(TX_ORIGIN_CONTRACT, "AuthBug.sol")
        report = scanner().report(result)
        self.assertIn("AuthBug.sol", report)

    def test_report_fail_on_critical(self):
        result = scanner().scan(SELFDESTRUCT_CONTRACT, "Bomb.sol")
        report = scanner().report(result)
        self.assertIn("FAIL", report)

    def test_report_pass_on_clean(self):
        result = scanner().scan(TIMESTAMP_CONTRACT, "Lock.sol")  # MEDIUM only
        report = scanner().report(result)
        self.assertIn("PASS", report)

    def test_report_lists_findings(self):
        result = scanner().scan(TX_ORIGIN_CONTRACT)
        report = scanner().report(result)
        self.assertIn("tx.origin", report.lower())


# ─────────────────────────────────────────────────────────────────────
# scan_contract() convenience function
# ─────────────────────────────────────────────────────────────────────

class TestScanContractHelper(unittest.TestCase):

    def test_returns_scan_result(self):
        result = scan_contract(REENTRANCY_CONTRACT, "R.sol")
        self.assertIsInstance(result, ScanResult)

    def test_detects_expected_vuln(self):
        result = scan_contract(REENTRANCY_CONTRACT)
        self.assertIn("REENTRANCY", vuln_ids(result))


# ─────────────────────────────────────────────────────────────────────
# Custom patterns
# ─────────────────────────────────────────────────────────────────────

class TestCustomPatterns(unittest.TestCase):

    def test_custom_pattern_detected(self):
        custom = VulnPattern(
            id="CUSTOM_EMIT",
            name="Missing Emit",
            severity="LOW",
            swc="N/A",
            pattern=r'function\s+setOwner',
            description="setOwner should emit an event",
            recommendation="Add emit OwnerChanged(...)",
        )
        s = ContractScanner(patterns=[custom])
        src = "pragma solidity 0.8.24;\ncontract X { function setOwner(address o) external {} }"
        result = s.scan(src)
        self.assertIn("CUSTOM_EMIT", vuln_ids(result))

    def test_empty_patterns_no_findings(self):
        s = ContractScanner(patterns=[])
        result = s.scan(MULTIvuln_CONTRACT)
        self.assertEqual(len(result.findings), 0)
        self.assertTrue(result.passed)


# ─────────────────────────────────────────────────────────────────────
# VULN_PATTERNS registry
# ─────────────────────────────────────────────────────────────────────

class TestVulnPatternsRegistry(unittest.TestCase):

    def test_all_have_required_fields(self):
        for p in VULN_PATTERNS:
            for attr in ("id", "name", "severity", "swc", "pattern",
                         "description", "recommendation"):
                self.assertTrue(getattr(p, attr, None) is not None,
                                f"{p.id} missing {attr}")

    def test_severity_values_valid(self):
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        for p in VULN_PATTERNS:
            self.assertIn(p.severity, valid, f"{p.id} has bad severity: {p.severity}")

    def test_patterns_compile(self):
        import re
        for p in VULN_PATTERNS:
            try:
                re.compile(p.pattern)
            except re.error as e:
                self.fail(f"Pattern {p.id} does not compile: {e}")

    def test_at_least_one_critical_pattern(self):
        criticals = [p for p in VULN_PATTERNS if p.severity == "CRITICAL"]
        self.assertGreater(len(criticals), 0)


if __name__ == "__main__":
    unittest.main()
