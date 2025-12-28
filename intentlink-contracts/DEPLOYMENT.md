# IntentLink Smart Contracts - Deployment Guide

This repository contains the smart contracts for **IntentLink**, an Account Abstraction (AA) intent execution layer built for the BlockDAG Hackathon.

## 🔗 Official Deployed Addresses

### **BlockDAG Awakening Testnet (Chain ID: 1043)**

- **RPC:** `https://rpc.awakening.bdagscan.com`
- **Explorer:** [https://awakening.bdagscan.com/](https://awakening.bdagscan.com/)

| Contract            | Address                                      | Verification Status |
| :------------------ | :------------------------------------------- | :------------------ |
| **IntentWallet**    | `0x718a09981d305c2293d0c85e9d957ad25cb2a1c7` | ✅ Verified         |
| **MockDEX**         | `0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56` | ✅ Verified         |
| **MockStakingFarm** | `0x1b227DF9c8D34CaB880774737FBf426E66Ba98Ed` | ✅ Verified         |
| **MockLending**     | `0xa23bDd28F9221F275897D8A26A8eb97A341cd257` | ✅ Verified         |

> **Note:** Contract addresses are also stored in `../data/BlockDAG Awakening Testnet/` directory.

### **Polygon Amoy Testnet (Chain ID: 80002)**

- **RPC:** `https://rpc-amoy.polygon.technology/`
- **Explorer:** [https://amoy.polygonscan.com/](https://amoy.polygonscan.com/)

| Contract            | Address                                      | Verification Status |
| :------------------ | :------------------------------------------- | :------------------ |
| **IntentWallet**    | `0x718a09981d305c2293d0c85e9d957ad25cb2a1c7` | ✅ Verified         |
| **MockDEX**         | `0xbC47d9625e7c102C6E9C08D29BbD3A76514eCB56` | ✅ Verified         |
| **MockStakingFarm** | `0x028f76d07112b560d04f5f172def1aa2879df364` | ✅ Verified         |
| **MockLending**     | `0x1b227df9c8d34cab880774737fbf426e66ba98ed` | ✅ Verified         |

> **Note:** Contract addresses are also stored in `../data/Polygon Amoy Testnet/` directory.

---

## 🛠️ Development & Deployment Workflow

Due to specific RPC configurations on the testnets, we utilize **Remix IDE** for reliable deployment and verification.

### **Prerequisites**

1.  **MetaMask** installed and configured with BlockDAG Awakening and Polygon Amoy networks.
2.  **Testnet Tokens:**
    - BDAG tokens (from [BlockDAG Faucet](https://faucet.bdagscan.com/))
    - POL tokens (from [Polygon Amoy Faucet](https://faucet.polygon.technology/))

### **Network Configuration for MetaMask**

**BlockDAG Awakening Testnet:**

```
Network Name: BlockDAG Awakening Testnet
RPC URL: https://rpc.awakening.bdagscan.com
Chain ID: 1043
Currency Symbol: BDAG
Block Explorer: https://awakening.bdagscan.com/
```

**Polygon Amoy Testnet:**

```
Network Name: Polygon Amoy Testnet
RPC URL: https://rpc-amoy.polygon.technology/
Chain ID: 80002
Currency Symbol: POL
Block Explorer: https://amoy.polygonscan.com/
```

### **Deployment Steps (Reproducible)**

#### **1. Prepare Remix IDE**

1.  Open [Remix IDE](https://remix.ethereum.org/)
2.  Create a new workspace or use the default
3.  Copy all contract files from this repository into Remix:
    - `IntentWallet.sol`
    - `MockDEX.sol`
    - `MockStakingFarm.sol`
    - `MockLending.sol`

#### **2. Compiler Settings**

1.  Navigate to the **Solidity Compiler** tab
2.  Configure:
    - **Compiler Version:** `0.8.26+commit.8a97fa7a`
    - **EVM Version:** `paris` (default)
    - **Optimization:** Enabled (200 runs)
3.  Click **Compile** for each contract

#### **3. Deploy IntentWallet**

1.  Navigate to **Deploy & Run Transactions** tab
2.  Configure:
    - **Environment:** `Injected Provider - MetaMask`
    - **Account:** Your wallet address (will be the initial owner)
    - **Contract:** Select `IntentWallet`
3.  **Constructor Argument:**
    - `initialOwner`: Paste your wallet address
4.  Click **Deploy** and confirm in MetaMask
5.  Wait for transaction confirmation
6.  Copy the deployed contract address

#### **4. Deploy Mock Protocols**

Repeat the deployment process for each mock protocol:

**MockDEX:**

- No constructor arguments required
- Deploy and save the address

**MockStakingFarm:**

- No constructor arguments required
- Deploy and save the address

**MockLending:**

- No constructor arguments required
- Deploy and save the address

#### **5. Whitelist Configuration**

After all contracts are deployed, configure the IntentWallet to trust the mock protocols:

1.  In Remix, select the deployed **IntentWallet** contract
2.  Call `setWhitelistStatus` for each protocol:
    ```solidity
    setWhitelistStatus(MockDEX_address, true)
    setWhitelistStatus(MockStakingFarm_address, true)
    setWhitelistStatus(MockLending_address, true)
    ```
3.  Confirm each transaction in MetaMask

#### **6. Contract Verification**

Both BlockDAG and Polygon explorers support automatic verification through Remix:

1.  In Remix, right-click on the deployed contract
2.  Select **Verify Contract**
3.  Follow the explorer's verification flow
4.  Alternatively, manually verify on the explorer using:
    - Contract source code
    - Compiler version: `0.8.26`
    - Optimization: Enabled (200 runs)
    - Constructor arguments (for IntentWallet)

---

## 📜 ABI & Integration

### **Contract ABIs**

Pre-compiled ABIs are available in the `../ABI/` directory:

- `IntentWallet.json`
- `MockDEX.json`
- `MockStakingFarm.json`
- `MockLending.json`

### **Artifacts**

Full compilation artifacts (including metadata) are in the `artifacts/` directory.

---

## 🔐 EIP-712 Signature Scheme

IntentLink uses **EIP-712** structured data signing for secure, off-chain intent authorization.

### **Domain Separator**

```json
{
  "name": "IntentLink",
  "version": "1",
  "chainId": 1043,
  "verifyingContract": "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7"
}
```

> **Note:** Change `chainId` to `80002` for Polygon Amoy deployments.

### **Message Types**

```json
{
  "Plan": [
    { "name": "planId", "type": "bytes32" },
    { "name": "planHash", "type": "bytes32" },
    { "name": "nonce", "type": "uint256" },
    { "name": "expiry", "type": "uint256" }
  ]
}
```

### **Signature Generation**

A reference implementation is available in `utils/generateSignature.js`:

```javascript
// Example usage
const signature = await generateSignature(
  planId,
  planHash,
  nonce,
  expiry,
  chainId,
  userPrivateKey
);
```

**Verification:**

```bash
node utils/generateSignature.js
# Expected output: Match: ✅ YES
```

---

## 🧪 Testing the Deployment

### **Quick Test Flow**

1.  **Approve Token:** Call `approve(intentWalletAddress, amount)` on a test ERC20
2.  **Execute Intent:** Call `executeIntent` on IntentWallet with:
    - Signature from EIP-712 signing
    - Target protocol address (whitelisted)
    - Encoded call data
3.  **Verify Execution:** Check transaction logs for `IntentExecuted` event

### **Backend Integration**

The IntentLink backend (Django) automatically:

1.  Parses natural language intents
2.  Generates execution plans
3.  Creates EIP-712 payloads for frontend signing
4.  Verifies signatures before execution
5.  Submits transactions to the blockchain

See the main [README.md](../README.md) for backend setup instructions.

---

## 📁 Repository Structure

```
intentlink-contracts/
├── IntentWallet.sol           # Main AA wallet contract
├── MockDEX.sol                # Mock DEX for testing
├── MockStakingFarm.sol        # Mock staking protocol
├── MockLending.sol            # Mock lending protocol
├── artifacts/                 # Remix compilation outputs
│   ├── IntentWallet.json
│   └── build-info/
├── utils/
│   └── generateSignature.js   # EIP-712 signature helper
├── .deps/                     # OpenZeppelin dependencies
└── DEPLOYMENT.md              # This file
```

---

## 🚀 Multi-Chain Support

IntentLink is designed for seamless multi-chain operation:

- **Identical Addresses:** IntentWallet and MockDEX use the same addresses across chains
- **Chain-Specific Protocols:** MockStaking and MockLending may differ per chain
- **Dynamic Configuration:** Backend automatically selects the correct RPC and contracts based on `chain_id`

---

## ⚠️ Security Considerations

### **For Production Deployments:**

1.  **Audit Smart Contracts:** Have contracts professionally audited before mainnet
2.  **Rotate Private Keys:** Never commit private keys to the repository
3.  **Timelock Upgrades:** Implement timelocks for contract upgrades
4.  **Rate Limiting:** Enforce rate limits on intent execution
5.  **Multi-Sig Ownership:** Transfer contract ownership to a multi-sig wallet

### **Current Testnet Configuration:**

- Contracts are owned by a single EOA (for hackathon purposes)
- Whitelisting is manually managed by the owner
- No formal audit has been conducted

---

## 📞 Support & Contact

- **GitHub:** [SheriffMudasir/IntentLink](https://github.com/SheriffMudasir/IntentLink)
- **Hackathon Track:** DeFi Speedway
- **Network:** BlockDAG Awakening Testnet

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

---

**Deployed with ❤️ using Remix IDE for the BlockDAG Hackathon 2025**
