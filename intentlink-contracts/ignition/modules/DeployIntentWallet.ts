// ignition/modules/DeployIntentWallet.ts

import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("IntentWalletModule", (m) => {
  // Get the first account from the configured network, which will be the deployer.
  // This address will be set as the initial owner of the IntentWallet contract.
  const initialOwner = m.getAccount(0);

  // Deploy the IntentWallet contract, passing the initialOwner address to its constructor.
  const intentWallet = m.contract("IntentWallet", [initialOwner]);

  // The module returns an object with the deployed contract instance.
  // This is useful for scripting and testing.
  return { intentWallet };
});