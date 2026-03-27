// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/DOFIdentityRegistry.sol";
import "../src/DOFReputationRegistry.sol";

contract DeployDOF is Script {
    function run() external {
        vm.startBroadcast();

        DOFIdentityRegistry identity = new DOFIdentityRegistry();
        DOFReputationRegistry reputation = new DOFReputationRegistry();

        console.log("DOFIdentityRegistry:", address(identity));
        console.log("DOFReputationRegistry:", address(reputation));

        vm.stopBroadcast();
    }
}
