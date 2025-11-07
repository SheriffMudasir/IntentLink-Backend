// hardhat.config.ts
import { HardhatUserConfig, configVariable } from "hardhat/config";
import "@nomicfoundation/hardhat-viem"; 
import * as dotenv from "dotenv";
dotenv.config();

const config: HardhatUserConfig = {
  solidity: "0.8.28",
  networks: {
    awakening: {
      url: configVariable("BLOCKDAG_RPC_URL"),
      accounts: [configVariable("DEPLOYER_PRIVATE_KEY")],
      chainId: 1043,
    },
  },
};

export default config;