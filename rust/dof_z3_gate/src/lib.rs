//! DOF Z3 Gate — Python bindings via PyO3.
//!
//! Exposes the Rust gate implementation to Python with zero-copy where possible.
//! Target: <1ms per evaluation (vs <10ms Python baseline).

use pyo3::prelude::*;

mod gate;
use gate::{Constraint, ConstraintPattern, DofGate, GateVerdict, compute_hash};

fn usize_min(a: usize, b: usize) -> usize {
    if a < b { a } else { b }
}

/// Python-facing gate evaluation result.
#[pyclass]
#[derive(Debug, Clone)]
pub struct PyGateResult {
    #[pyo3(get)]
    pub verdict: String,           // "APPROVED" | "REJECTED" | "TIMEOUT"
    #[pyo3(get)]
    pub violated_constraint: Option<String>,
    #[pyo3(get)]
    pub reason: Option<String>,
    #[pyo3(get)]
    pub proof_hash: String,
    #[pyo3(get)]
    pub latency_us: u64,           // microseconds
}

#[pymethods]
impl PyGateResult {
    fn __repr__(&self) -> String {
        format!(
            "GateResult(verdict={}, latency={}µs, proof={}...)",
            self.verdict,
            self.latency_us,
            &self.proof_hash[..usize_min(18, self.proof_hash.len())]
        )
    }

    fn is_approved(&self) -> bool {
        self.verdict == "APPROVED"
    }
}

/// Python-facing DOF gate.
#[pyclass]
pub struct PyDofGate {
    inner: DofGate,
}

#[pymethods]
impl PyDofGate {
    /// Create a new gate with default DOF governance constraints.
    #[new]
    pub fn new() -> Self {
        Self {
            inner: DofGate::new(DofGate::default_constraints()),
        }
    }

    /// Evaluate a single output string against all constraints.
    /// Returns a PyGateResult with verdict and proof hash.
    pub fn evaluate(&self, output: &str) -> PyGateResult {
        let t0 = std::time::Instant::now();
        let verdict = self.inner.evaluate(output);
        let latency_us = t0.elapsed().as_micros() as u64;
        let proof_hash = self.inner.proof_hash(output, &verdict);

        match verdict {
            GateVerdict::Approved => PyGateResult {
                verdict: "APPROVED".to_string(),
                violated_constraint: None,
                reason: None,
                proof_hash,
                latency_us,
            },
            GateVerdict::Rejected { violated_constraint, reason } => PyGateResult {
                verdict: "REJECTED".to_string(),
                violated_constraint: Some(violated_constraint),
                reason: Some(reason),
                proof_hash,
                latency_us,
            },
            GateVerdict::Timeout => PyGateResult {
                verdict: "TIMEOUT".to_string(),
                violated_constraint: None,
                reason: Some("Constraint evaluation timed out".to_string()),
                proof_hash,
                latency_us,
            },
        }
    }

    /// Compute SHA3-256 hash of a string (Solidity-compatible).
    #[staticmethod]
    pub fn hash(input: &str) -> String {
        compute_hash(input)
    }

    /// Check if the Rust gate module loaded correctly.
    #[staticmethod]
    pub fn health_check() -> bool {
        true
    }
}

/// Module definition — exposes to Python as `dof_z3_gate`
#[pymodule]
fn dof_z3_gate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDofGate>()?;
    m.add_class::<PyGateResult>()?;
    m.add("__version__", "0.1.0")?;
    m.add("__description__", "DOF-MESH Z3 Gate — Rust implementation (<1ms)")?;
    Ok(())
}
