# 🔗 IntentLink Smart Contracts

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.26-e6e6e6?logo=solidity&logoColor=black)](https://soliditylang.org/)
[![Deployed](https://img.shields.io/badge/Status-Deployed%20%26%20Verified-brightgreen)](./DEPLOYMENT.md)

Smart contract suite for **IntentLink** - an Account Abstraction (AA) intent execution layer enabling natural language DeFi interactions on BlockDAG and Polygon networks.

---

## 📋 Overview

This directory contains the Solidity smart contracts that power IntentLink's on-chain operations:

- **IntentWallet.sol** - Core AA wallet with EIP-712 signature verification and whitelisting
- **MockDEX.sol** - Mock DEX for token swaps (testing/demo)
- **MockStakingFarm.sol** - Mock staking protocol (testing/demo)
- **MockLending.sol** - Mock lending protocol (testing/demo)

---

## 🚀 Quick Start

### **Deployed & Verified Contracts**

All contracts are **live and verified** on two testnets:

| Network                       | IntentWallet                                 | Explorer                                                                                  |
| ----------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **BlockDAG Awakening** (1043) | `0x718a09981d305c2293d0c85e9d957ad25cb2a1c7` | [View](https://awakening.bdagscan.com/address/0x718a09981d305c2293d0c85e9d957ad25cb2a1c7) |
| **Polygon Amoy** (80002)      | `0x718a09981d305c2293d0c85e9d957ad25cb2a1c7` | [View](https://amoy.polygonscan.com/address/0x718a09981d305c2293d0c85e9d957ad25cb2a1c7)   |

📖 **Full deployment details:** See [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 🏗️ Architecture

### **IntentWallet (Core Contract)**

The main contract implementing Account Abstraction principles:

```solidity
contract IntentWallet is EIP712, Ownable, Pausable, ReentrancyGuard
```

**Key Features:**

- ✅ **EIP-712 Signature Verification** - Cryptographic proof of user intent
- ✅ **Whitelist System** - Only approved protocols can be called
- ✅ **Emergency Pause** - Circuit breaker for security incidents
- ✅ **Reentrancy Protection** - SafeGuards against reentrancy attacks
- ✅ **Multi-Chain Support** - Identical deployment across chains

**Core Functions:**

```solidity
// Execute an approved intent with signature verification
function executeIntent(
    bytes32 planId,
    bytes32 planHash,
    uint256 nonce,
    uint256 expiry,
    bytes calldata signature,
    address target,
    bytes calldata data
) external nonReentrant whenNotPaused

// Owner configures trusted protocols
function setWhitelistStatus(address target, bool status) external onlyOwner
```

### **Mock Protocols**

Demo contracts simulating real DeFi protocols:

**MockDEX** - Token swapping

```solidity
function swap(address fromToken, address toToken, uint256 amount) external
```

**MockStakingFarm** - Token staking with rewards

```solidity
function stake(uint256 amount) external
function unstake(uint256 amount) external
```

**MockLending** - Lending/borrowing operations

```solidity
function deposit(uint256 amount) external
function borrow(uint256 amount) external
```

---

## 🔐 Security Features

### **EIP-712 Typed Data Signing**

All intent executions require a valid EIP-712 signature:

**Domain:**

```json
{
  "name": "IntentLink",
  "version": "1",
  "chainId": 1043,
  "verifyingContract": "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7"
}
```

**Message Schema:**

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

Use the provided utility script:

```bash
cd utils
node generateSignature.js
```

Expected output:

```
✅ Signature generated successfully
🔐 planHash matches: ✅ YES
```

### **Security Mechanisms**

1. **Whitelist Enforcement** - Only owner-approved contracts are callable
2. **Signature Expiry** - Time-limited authorization (default: 1 hour)
3. **Nonce Tracking** - Prevents replay attacks
4. **Pausable** - Emergency circuit breaker
5. **ReentrancyGuard** - Protection against reentrancy exploits

---

## 📁 Project Structure

```
intentlink-contracts/
├── IntentWallet.sol              # Core AA wallet contract
├── MockDEX.sol                   # Mock DEX protocol
├── MockStakingFarm.sol           # Mock staking protocol
├── MockLending.sol               # Mock lending protocol
├── DEPLOYMENT.md                 # Deployment guide & addresses
├── README.md                     # This file
├── .gitignore                    # Git ignore rules
├── package.json                  # Node.js dependencies (utils)
├── remix.config.json             # Remix IDE configuration
├── utils/
│   └── generateSignature.js      # EIP-712 signature helper
├── artifacts/                    # Compilation artifacts (gitignored)
│   ├── IntentWallet.json
│   └── build-info/
└── .deps/                        # OpenZeppelin libs (gitignored)
    └── npm/@openzeppelin/
```

---

## 🛠️ Development

### **Prerequisites**

- [Remix IDE](https://remix.ethereum.org/) (primary development environment)
- [MetaMask](https://metamask.io/) with testnet funds
- Node.js 18+ (for signature utilities)

### **Compilation**

1. Open [Remix IDE](https://remix.ethereum.org/)
2. Import contracts from this repository
3. Configure compiler:
   - **Version:** `0.8.26`
   - **EVM:** `paris`
   - **Optimization:** Enabled (200 runs)
4. Click **Compile**

### **Local Testing**

For signature verification testing:

```bash
cd utils
npm install
node generateSignature.js
```

### **Deployment**

See [DEPLOYMENT.md](./DEPLOYMENT.md) for step-by-step deployment instructions.

---

## 📦 ABIs & Integration

### **Contract ABIs**

Pre-compiled ABIs are available in `../ABI/`:

- `IntentWallet.json`
- `MockDEX.json`
- `MockStakingFarm.json`
- `MockLending.json`

### **Backend Integration**

The IntentLink backend (Django) uses these contracts for:

1. Parsing natural language intents
2. Generating execution plans
3. Creating EIP-712 payloads
4. Verifying signatures
5. Submitting transactions

See the main [README.md](../README.md) for backend setup.

---

## 🌐 Multi-Chain Deployment

IntentLink supports **deterministic deployment** across chains:

| Contract     | BlockDAG (1043) | Polygon Amoy (80002) | Same Address? |
| ------------ | --------------- | -------------------- | ------------- |
| IntentWallet | `0x718a...`     | `0x718a...`          | ✅ Yes        |
| MockDEX      | `0xbC47...`     | `0xbC47...`          | ✅ Yes        |
| MockStaking  | `0x1b22...`     | `0x028f...`          | ❌ No         |
| MockLending  | `0xa23b...`     | `0x1b22...`          | ❌ No         |

**Why identical addresses?**

- Same deployment order
- Same nonce/salt
- Deterministic CREATE opcode behavior

**Backend handles multi-chain via:**

```python
# settings.py
NETWORK_CONFIG = {
    1043: {  # BlockDAG
        "chain_name": "BlockDAG Awakening Testnet",
        "contracts": {
            "intent_wallet": "0x718a09981d305c2293d0c85e9d957ad25cb2a1c7",
            # ...
        }
    },
    80002: {  # Polygon
        # ...
    }
}
```

---

## 🧪 Testing Strategy

### **Unit Tests** (On-Chain)

- ✅ Signature verification with valid/invalid signatures
- ✅ Whitelist enforcement
- ✅ Nonce replay protection
- ✅ Expiry validation
- ✅ Emergency pause functionality

### **Integration Tests** (Backend)

- ✅ End-to-end intent execution flow
- ✅ Multi-chain configuration validation
- ✅ EIP-712 signature generation/verification
- ✅ Contract interaction (approve → execute)

### **Test Files**

Located in parent directory:

- `../test_signature.py` - Signature verification tests
- `../test_multichain.py` - Multi-chain config tests

---

## 🔍 Contract Verification

All contracts are **verified on block explorers:**

**BlockDAG Awakening:**

- [IntentWallet](https://awakening.bdagscan.com/address/0x718a09981d305c2293d0c85e9d957ad25cb2a1c7)
- Source code visible with green checkmark ✅

**Polygon Amoy:**

- [IntentWallet](https://amoy.polygonscan.com/address/0x718a09981d305c2293d0c85e9d957ad25cb2a1c7)
- Source code verified with matching bytecode ✅

---

## ⚠️ Production Considerations

### **Current Status: Testnet Demo**

This codebase is designed for hackathon/testnet usage. Before mainnet:

1. ✅ **Audit Required** - Professional security audit
2. ✅ **Formal Verification** - Symbolic execution tools
3. ✅ **Multi-Sig Ownership** - Replace single EOA owner
4. ✅ **Timelock Upgrades** - Add upgrade delay mechanism
5. ✅ **Insurance Fund** - Risk mitigation for exploits

### **Known Limitations**

- Single owner wallet (centralization risk)
- No upgrade mechanism (immutable deployment)
- Mock protocols (not real DeFi integrations)
- Limited nonce tracking (off-chain in backend)

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](../LICENSE) for details.

---

## 🤝 Contributing

This is a hackathon submission. For production use:

1. Fork the repository
2. Add comprehensive tests
3. Implement upgrade patterns (proxy/diamond)
4. Get security audits
5. Submit PR with detailed documentation

---

## 📞 Contact & Resources

- **GitHub:** [SheriffMudasir/IntentLink](https://github.com/SheriffMudasir/IntentLink)
- **Hackathon:** BlockDAG DeFi Speedway Track
- **Documentation:** See parent [README.md](../README.md)
- **Deployment Guide:** [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Built with ❤️ using Remix IDE for BlockDAG Hackathon 2025**
