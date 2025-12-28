// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// Interface to interact with our specific MockStakingFarmV2
interface IStakingFarm {
    function getPosition(
        address user
    ) external view returns (uint256 staked, uint256 rewards, uint256 apy);
}

/**
 * @title IntentWalletV2
 * @author IntentLink Team
 * @notice V2 adds Portfolio Aggregation for the Frontend Dashboard.
 */
contract IntentWalletV2 is Ownable, Pausable, ReentrancyGuard, EIP712 {
    // --- Data Structures ---
    struct Plan {
        bytes32 planId;
        bytes32 planHash;
        uint256 nonce;
        uint256 expiry;
    }

    struct PortfolioView {
        uint256 walletBalance; // User's liquid MockUSDT
        uint256 stakedBalance; // User's staked amount
        uint256 pendingRewards; // Rewards waiting to be claimed
        uint256 currentAPY; // Live APY from the farm
        uint256 ethBalance; // User's Native Token (BDAG/POL) balance
    }

    // --- State Variables ---
    mapping(address => uint256) public nonces;
    mapping(address => bool) public isTargetWhitelisted;
    mapping(address => bool) public isRelayerAuthorized;

    bytes32 private constant _PLAN_TYPEHASH =
        keccak256(
            "Plan(bytes32 planId,bytes32 planHash,uint256 nonce,uint256 expiry)"
        );

    // --- Events ---
    event IntentExecuted(
        address indexed user,
        bytes32 indexed planId,
        bytes32 cidHash,
        address indexed relayer,
        uint256 nonce
    );
    event TargetWhitelistUpdated(address indexed target, bool isAllowed);
    event RelayerAuthorizationUpdated(address indexed relayer, bool isAllowed);

    constructor(
        address initialOwner
    ) Ownable(initialOwner) EIP712("IntentLink", "1") {}

    // --- Core Execution Logic (Same as V1 for backward compatibility) ---
    function executeBatch(
        address user,
        Plan calldata plan,
        address[] calldata targets,
        bytes[] calldata calldatas,
        bytes32 cidHash,
        bytes calldata signature
    ) external nonReentrant whenNotPaused {
        require(isRelayerAuthorized[msg.sender], "Not an authorized relayer");
        require(block.timestamp <= plan.expiry, "Plan expired");
        require(targets.length == calldatas.length, "Mismatched arrays");
        require(
            targets.length > 0 && targets.length <= 15,
            "Invalid batch size"
        );

        _verifyPlanSignature(user, plan, signature);
        nonces[user]++;

        for (uint256 i = 0; i < targets.length; i++) {
            require(isTargetWhitelisted[targets[i]], "Target not whitelisted");
            (bool success, bytes memory result) = targets[i].call(calldatas[i]);
            if (!success) {
                assembly {
                    revert(add(result, 32), mload(result))
                }
            }
        }

        emit IntentExecuted(user, plan.planId, cidHash, msg.sender, plan.nonce);
    }

    // --- Portfolio View Function (The UX Fix) ---
    /**
     * @notice Fetches all dashboard data in a single RPC call.
     * @param user The user wallet address
     * @param token The MockUSDT address
     * @param farm The MockStakingFarmV2 address
     */
    function getPortfolio(
        address user,
        address token,
        address farm
    ) external view returns (PortfolioView memory) {
        // 1. Get Wallet Token Balance
        uint256 bal = IERC20(token).balanceOf(user);

        // 2. Get Staking Data (Staked, Rewards, APY) from the V2 Farm
        (uint256 staked, uint256 rewards, uint256 apy) = IStakingFarm(farm)
            .getPosition(user);

        return
            PortfolioView({
                walletBalance: bal,
                stakedBalance: staked,
                pendingRewards: rewards,
                currentAPY: apy,
                ethBalance: user.balance
            });
    }

    // --- Internal & Admin (Same as V1) ---
    function _verifyPlanSignature(
        address user,
        Plan calldata plan,
        bytes memory signature
    ) private view {
        bytes32 digest = _hashTypedDataV4(
            keccak256(
                abi.encode(
                    _PLAN_TYPEHASH,
                    plan.planId,
                    plan.planHash,
                    plan.nonce,
                    plan.expiry
                )
            )
        );
        address signer = ECDSA.recover(digest, signature);
        require(signer == user, "Invalid signature");
        require(nonces[signer] == plan.nonce, "Invalid nonce");
    }

    function setWhitelistStatus(
        address target,
        bool isAllowed
    ) external onlyOwner {
        isTargetWhitelisted[target] = isAllowed;
        emit TargetWhitelistUpdated(target, isAllowed);
    }

    function setRelayerAuthorization(
        address relayer,
        bool isAuthorized
    ) external onlyOwner {
        isRelayerAuthorized[relayer] = isAuthorized;
        emit RelayerAuthorizationUpdated(relayer, isAuthorized);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
