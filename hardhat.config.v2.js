// Temp config for V2 deploy — excludes contracts/tempo (forge-std dependency)
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: ".env", override: false });

module.exports = {
  paths: {
    sources: "./contracts_v2_build",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  solidity: {
    compilers: [
      { version: "0.8.20" }
    ]
  },
  networks: {
    conflux_testnet: {
      url: "https://evmtestnet.confluxrpc.com",
      chainId: 71,
      accounts: process.env.CONFLUX_PRIVATE_KEY ? [process.env.CONFLUX_PRIVATE_KEY] :
                process.env.conflux_PRIVATE_KEY ? [process.env.conflux_PRIVATE_KEY] : []
    }
  },
};
