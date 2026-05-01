require("@nomicfoundation/hardhat-toolbox");

const os = require("os");
const path = require("path");

module.exports = {
  paths: {
    sources: "./contracts_hardhat/proof_registry",
    cache: path.join(os.tmpdir(), "dof-mesh-hardhat-proof-registry-cache"),
    artifacts: path.join(os.tmpdir(), "dof-mesh-hardhat-proof-registry-artifacts")
  },
  solidity: {
    compilers: [
      { version: "0.8.19" },
      { version: "0.8.20" },
      { version: "0.8.27" }
    ]
  }
};
