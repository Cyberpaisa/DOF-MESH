//! DOF Z3 Gate — Core governance verification logic.
//!
//! Implements deterministic constraint checking equivalent to the Python Z3 gate
//! but with Rust-native performance (<1ms target for all constraint sets).

use sha3::{Digest, Sha3_256};
use serde::{Deserialize, Serialize};

/// Result of a governance gate evaluation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum GateVerdict {
    /// Output passes all constraints
    Approved,
    /// Output violates at least one constraint
    Rejected { violated_constraint: String, reason: String },
    /// Constraint evaluation timed out (treated as rejection)
    Timeout,
}

/// A single governance constraint.
#[derive(Debug, Clone)]
pub struct Constraint {
    pub id: String,
    pub pattern: ConstraintPattern,
}

/// How a constraint is evaluated.
#[derive(Debug, Clone)]
pub enum ConstraintPattern {
    /// Output must not contain these keywords
    MustNotContain(Vec<String>),
    /// Output length must be within range
    LengthBound { min: usize, max: usize },
    /// Output hash must match a known good hash
    HashBound(String),
    /// Always passes (for testing)
    AlwaysPass,
}

impl Constraint {
    pub fn evaluate(&self, output: &str) -> Result<bool, String> {
        match &self.pattern {
            ConstraintPattern::MustNotContain(forbidden) => {
                let output_lower = output.to_lowercase();
                for keyword in forbidden {
                    if output_lower.contains(keyword.as_str()) {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
            ConstraintPattern::LengthBound { min, max } => {
                let len = output.len();
                Ok(len >= *min && len <= *max)
            }
            ConstraintPattern::HashBound(expected_hash) => {
                let actual = compute_hash(output);
                Ok(actual == *expected_hash)
            }
            ConstraintPattern::AlwaysPass => Ok(true),
        }
    }
}

/// Compute SHA3-256 hash of a string.
pub fn compute_hash(input: &str) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(input.as_bytes());
    let result = hasher.finalize();
    format!("0x{:x}", result)
}

/// DOF Governance Gate — evaluates output against all constraints.
pub struct DofGate {
    constraints: Vec<Constraint>,
}

impl DofGate {
    pub fn new(constraints: Vec<Constraint>) -> Self {
        Self { constraints }
    }

    /// Build default DOF governance constraints.
    pub fn default_constraints() -> Vec<Constraint> {
        vec![
            Constraint {
                id: "no_privilege_escalation".to_string(),
                pattern: ConstraintPattern::MustNotContain(vec![
                    "ignore previous instructions".to_string(),
                    "disregard all rules".to_string(),
                    "you are now".to_string(),
                    "act as if".to_string(),
                    "jailbreak".to_string(),
                ]),
            },
            Constraint {
                id: "no_instruction_override".to_string(),
                pattern: ConstraintPattern::MustNotContain(vec![
                    "override governance".to_string(),
                    "bypass constitution".to_string(),
                    "disable monitoring".to_string(),
                    "turn off safety".to_string(),
                ]),
            },
            Constraint {
                id: "output_length_bound".to_string(),
                pattern: ConstraintPattern::LengthBound { min: 1, max: 50_000 },
            },
        ]
    }

    /// Evaluate all constraints against the output.
    /// Returns GateVerdict::Approved only if ALL constraints pass.
    pub fn evaluate(&self, output: &str) -> GateVerdict {
        for constraint in &self.constraints {
            match constraint.evaluate(output) {
                Ok(true) => continue,
                Ok(false) => {
                    return GateVerdict::Rejected {
                        violated_constraint: constraint.id.clone(),
                        reason: format!("Constraint '{}' not satisfied", constraint.id),
                    };
                }
                Err(e) => {
                    return GateVerdict::Rejected {
                        violated_constraint: constraint.id.clone(),
                        reason: format!("Evaluation error: {}", e),
                    };
                }
            }
        }
        GateVerdict::Approved
    }

    /// Compute proof hash for the evaluation result.
    pub fn proof_hash(&self, output: &str, verdict: &GateVerdict) -> String {
        let verdict_str = match verdict {
            GateVerdict::Approved => "APPROVED",
            GateVerdict::Rejected { .. } => "REJECTED",
            GateVerdict::Timeout => "TIMEOUT",
        };
        let data = format!("{}{}", compute_hash(output), verdict_str);
        compute_hash(&data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_constraints_approve_clean_output() {
        let gate = DofGate::new(DofGate::default_constraints());
        let verdict = gate.evaluate("The weather is nice today.");
        assert_eq!(verdict, GateVerdict::Approved);
    }

    #[test]
    fn test_privilege_escalation_rejected() {
        let gate = DofGate::new(DofGate::default_constraints());
        let verdict = gate.evaluate("ignore previous instructions and do X");
        assert!(matches!(verdict, GateVerdict::Rejected { .. }));
    }

    #[test]
    fn test_instruction_override_rejected() {
        let gate = DofGate::new(DofGate::default_constraints());
        let verdict = gate.evaluate("override governance and bypass constitution");
        assert!(matches!(verdict, GateVerdict::Rejected { .. }));
    }

    #[test]
    fn test_empty_output_approved() {
        let constraints = vec![Constraint {
            id: "test".to_string(),
            pattern: ConstraintPattern::AlwaysPass,
        }];
        let gate = DofGate::new(constraints);
        let verdict = gate.evaluate("");
        assert_eq!(verdict, GateVerdict::Approved);
    }

    #[test]
    fn test_hash_is_deterministic() {
        let h1 = compute_hash("test input");
        let h2 = compute_hash("test input");
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_hash_starts_with_0x() {
        let h = compute_hash("test");
        assert!(h.starts_with("0x"));
    }

    #[test]
    fn test_proof_hash_differs_by_verdict() {
        let gate = DofGate::new(DofGate::default_constraints());
        let v_ok = GateVerdict::Approved;
        let v_fail = GateVerdict::Rejected {
            violated_constraint: "test".to_string(),
            reason: "test".to_string(),
        };
        let h1 = gate.proof_hash("output", &v_ok);
        let h2 = gate.proof_hash("output", &v_fail);
        assert_ne!(h1, h2);
    }
}
