// utils\generateSignature.js

const { ethers } = require("ethers");

// --- CONFIGURATION ---
// Replace these with your actual deployed address and chain ID
const CONTRACT_ADDRESS = "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7";
const CHAIN_ID = 1043; // 1043 for BlockDAG, 80002 for Amoy

// --- EIP-712 DOMAIN ---
const domain = {
    name: "IntentLink",
    version: "1",
    chainId: CHAIN_ID,
    verifyingContract: CONTRACT_ADDRESS,
};

// --- EIP-712 TYPES ---
// This matches the struct Plan in IntentWallet.sol
const types = {
    Plan: [
        { name: "planId", type: "bytes32" },
        { name: "planHash", type: "bytes32" },
        { name: "nonce", type: "uint256" },
        { name: "expiry", type: "uint256" },
    ],
};

async function main() {
    // 1. Create a random wallet to simulate the user
    const wallet = ethers.Wallet.createRandom();
    console.log("User Address:", wallet.address);

    // 2. Define the Plan data (Example)
    // In a real scenario, 'planHash' is the keccak256 of the targets/calldata array
    // For this test, we just use a dummy hash
    const samplePlan = {
        planId: ethers.id("plan-123"), // Unique ID for the plan
        planHash: ethers.keccak256(ethers.toUtf8Bytes("Execute swap and stake")), 
        nonce: 0,
        expiry: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
    };

    console.log("\n--- Data to Sign ---");
    console.log(samplePlan);

    // 3. Sign the Typed Data
    // ethers.js handles the EIP-712 hashing automatically
    const signature = await wallet.signTypedData(domain, types, samplePlan);

    console.log("\n--- Signature ---");
    console.log(signature);

    // 4. Verify (Simulation of what the Smart Contract does)
    const recoveredAddress = ethers.verifyTypedData(domain, types, samplePlan, signature);

    console.log("\n--- Verification ---");
    console.log("Recovered:", recoveredAddress);
    console.log("Original: ", wallet.address);
    console.log("Match:    ", recoveredAddress === wallet.address ? "✅ YES" : "❌ NO");
}

main().catch(console.error);