// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title IntentYieldVault
 * @dev A Wave 4 Flagship Primitive.
 * Features: Time-Lock Multipliers, Auto-Compounding, and Early Exit Penalties.
 * Designed for High-Frequency Intent Execution on BlockDAG.
 */
contract IntentYieldVault is ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;

    IERC20 public stakingToken;

    struct UserInfo {
        uint256 amount; // Amount staked
        uint256 rewardDebt; // Rewards already calculated but not claimed
        uint256 lastUpdateTime; // Timestamp of last interaction
        uint256 lockEndTime; // When the lock expires
        uint256 multiplier; // APY Multiplier (100 = 1x, 300 = 3x)
    }

    mapping(address => UserInfo) public userInfo;

    // Base Reward Rate: ~10% APY equivalent
    uint256 public constant BASE_RATE_PER_SECOND = 100;

    // Events for the Dashboard
    event Staked(address indexed user, uint256 amount, uint256 lockDuration);
    event Withdrawn(address indexed user, uint256 amount, bool earlyPenalty);
    event Compounded(address indexed user, uint256 rewardsAdded);

    constructor(
        address _stakingToken,
        address _initialOwner
    ) Ownable(_initialOwner) {
        stakingToken = IERC20(_stakingToken);
    }

    // --- Core Logic ---

    /**
     * @notice Stakes tokens with a specific lock period for higher yield.
     * @param onBehalfOf The user receiving the stake (Account Abstraction).
     * @param amount The amount to stake.
     * @param lockType 0 = Flexible, 1 = 7 Days, 2 = 30 Days.
     */
    function stakeFor(
        address onBehalfOf,
        uint256 amount,
        uint8 lockType
    ) external nonReentrant {
        _updateReward(onBehalfOf);

        // Pull tokens from the caller (IntentWallet)
        if (amount > 0) {
            stakingToken.safeTransferFrom(msg.sender, address(this), amount);
            userInfo[onBehalfOf].amount += amount;
        }

        // Set Lock & Multiplier
        uint256 duration = 0;
        uint256 mult = 100; // 1x

        if (lockType == 1) {
            duration = 7 days;
            mult = 150;
        }
        if (lockType == 2) {
            duration = 30 days;
            mult = 300;
        }

        // Extend lock if new stake has longer duration
        uint256 newLockEnd = block.timestamp + duration;
        if (newLockEnd > userInfo[onBehalfOf].lockEndTime) {
            userInfo[onBehalfOf].lockEndTime = newLockEnd;
            userInfo[onBehalfOf].multiplier = mult;
        }

        emit Staked(onBehalfOf, amount, duration);
    }

    /**
     * @notice Reinvests pending rewards into the principal stake.
     */
    function compoundFor(address onBehalfOf) external nonReentrant {
        _updateReward(onBehalfOf);

        uint256 pending = userInfo[onBehalfOf].rewardDebt;
        if (pending > 0) {
            userInfo[onBehalfOf].rewardDebt = 0;
            userInfo[onBehalfOf].amount += pending;
            emit Compounded(onBehalfOf, pending);
        }
    }

    /**
     * @notice Withdraws funds. Applies 10% penalty if locked.
     */
    function withdraw(uint256 amount) external nonReentrant {
        UserInfo storage user = userInfo[msg.sender];
        require(user.amount >= amount, "Insufficient balance");

        _updateReward(msg.sender);

        uint256 amountToSend = amount;
        bool penaltyApplied = false;

        // Early Exit Penalty Check
        if (block.timestamp < user.lockEndTime) {
            uint256 penalty = (amount * 10) / 100;
            amountToSend -= penalty;
            penaltyApplied = true;
            // Burn penalty (simulated by not sending it for now)
        }

        user.amount -= amount;
        stakingToken.safeTransfer(msg.sender, amountToSend);

        emit Withdrawn(msg.sender, amountToSend, penaltyApplied);
    }

    // --- Internal Helpers ---

    function _updateReward(address account) internal {
        if (userInfo[account].lastUpdateTime == 0) {
            userInfo[account].lastUpdateTime = block.timestamp;
            return;
        }

        uint256 newRewards = _calculatePending(account);
        userInfo[account].rewardDebt += newRewards;
        userInfo[account].lastUpdateTime = block.timestamp;
    }

    function _calculatePending(
        address account
    ) internal view returns (uint256) {
        UserInfo memory user = userInfo[account];
        if (user.amount == 0) return 0;

        uint256 timeElapsed = block.timestamp - user.lastUpdateTime;

        // Math: Balance * Time * BaseRate * Multiplier / 100
        return
            (user.amount *
                timeElapsed *
                BASE_RATE_PER_SECOND *
                user.multiplier) /
            100 /
            1e15;
    }

    // --- View Functions (Frontend Dashboard) ---

    function getPosition(
        address user
    )
        external
        view
        returns (
            uint256 staked,
            uint256 rewards,
            uint256 apy,
            uint256 unlockTime
        )
    {
        UserInfo memory u = userInfo[user];
        uint256 pending = u.rewardDebt + _calculatePending(user);

        // Calculate dynamic APY based on multiplier
        // Base 12% * Multiplier
        uint256 dynamicAPY = (1200 * u.multiplier) / 100;

        return (u.amount, pending, dynamicAPY, u.lockEndTime);
    }
}
