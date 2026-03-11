require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.19",
  networks: {
    avalanche: {
      url: process.env.AVALANCHE_RPC_URL || "https://api.avax.network/ext/bc/C/rpc",
      chainId: 43114,
      accounts: process.env.AVALANCHE_PRIVATE_KEY ? [process.env.AVALANCHE_PRIVATE_KEY] : [],
    },
    fuji: {
      url: "https://api.avax-test.network/ext/bc/C/rpc",
      chainId: 43113,
      accounts: process.env.AVALANCHE_PRIVATE_KEY ? [process.env.AVALANCHE_PRIVATE_KEY] : [],
    },
    conflux_testnet: {
      url: "https://evmtestnet.confluxrpc.com",
      chainId: 71,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    conflux: {
      url: "https://evm.confluxrpc.com",
      chainId: 1030,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    base_sepolia: {
      url: "https://sepolia.base.org",
      chainId: 84532,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    base: {
      url: "https://mainnet.base.org",
      chainId: 8453,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    arbitrum_sepolia: {
      url: "https://sepolia-rollup.arbitrum.io/rpc",
      chainId: 421614,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    arbitrum: {
      url: "https://arb1.arbitrum.io/rpc",
      chainId: 42161,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    polygon_amoy: {
      url: "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    polygon: {
      url: "https://polygon-rpc.com",
      chainId: 137,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    celo_alfajores: {
      url: "https://alfajores-forno.celo-testnet.org",
      chainId: 44787,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    celo: {
      url: "https://forno.celo.org",
      chainId: 42220,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    },
    sepolia: {
      url: "https://ethereum-sepolia-rpc.publicnode.com",
      chainId: 11155111,
      accounts: process.env.DOF_PRIVATE_KEY ? [process.env.DOF_PRIVATE_KEY] : []
    }
  },
};
