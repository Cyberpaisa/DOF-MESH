require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// Config mínima solo para deploy en SKALE Europa
// No incluye contratos de Forge (tempo/) que rompen la compilación de Hardhat
module.exports = {
  paths: {
    sources: "./contracts_skale_deploy",
    cache: "./cache_skale",
    artifacts: "./artifacts_skale"
  },
  solidity: {
    compilers: [
      {
        version: "0.8.19",
        settings: {
          evmVersion: "london",
          optimizer: { enabled: true, runs: 200 }
        }
      }
    ]
  },
  networks: {
    skale_europa: {
      url: "https://mainnet.skalenodes.com/v1/elated-tan-skat",
      chainId: 2046399126,
      accounts: process.env.CHAIN_AGNOSTIC_PRIVATE_KEY ? [process.env.CHAIN_AGNOSTIC_PRIVATE_KEY] : [],
      gas: 8000000,
      gasPrice: 100000
    }
  }
};
