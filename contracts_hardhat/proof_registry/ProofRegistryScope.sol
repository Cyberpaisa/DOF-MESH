// SPDX-License-Identifier: MIT
pragma solidity >=0.8.19 <0.9.0;

// Scoped Hardhat compile entrypoint for proof registry behavior tests.
// This file intentionally imports only the contracts needed for the
// proof registry test surface, avoiding the Foundry workspace under
// contracts/tempo/.

import "../../contracts/DOFProofRegistry.sol";
import "../../contracts/DOFValidationRegistry.sol";
import "../../contracts/DOFEvaluator.sol";
