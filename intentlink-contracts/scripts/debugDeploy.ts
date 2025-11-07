// scripts/debugDeploy.ts
import hre from "hardhat";

async function main() {
  console.log("🚀 Starting direct deployment script...");

  // 1. Get the deployer account
  const [deployer] = await hre.viem.getWalletClients();
  console.log(` Deployer Address: ${deployer.account.address}`);

  // 2. Deploy the IntentWallet contract
  console.log(" Deploying IntentWallet contract...");
  const intentWallet = await hre.viem.deployContract("IntentWallet", [
    deployer.account.address, // Pass the deployer's address as initialOwner
  ]);

  console.log("✅ IntentWallet deployed successfully!");
  console.log(` Contract Address: ${intentWallet.address}`);
}

main().catch((error) => {
  console.error("❌ Deployment failed!");
  console.error(error);
  process.exitCode = 1;
});