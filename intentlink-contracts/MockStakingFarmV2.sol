// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/**
 * @title MockStakingFarmV2
 * @dev Simulates a Staking Protocol with APY and Reward tracking.
 * NOTE: We mocks the logic using Native Coin (BDAG) logic for simplicity,
 * or abstract units if just calling the function without msg.value.
 */
contract MockStakingFarmV2 {
    // --- State ---
    mapping(address => uint256) public stakedBalance;
    mapping(address => uint256) public rewardBalance;
    mapping(address => uint256) public lastUpdateTime;

    // Simulation: 12% APY (approx 0.0000000038 tokens per second per token)
    uint256 public constant REWARD_RATE_PER_SECOND = 100;

    // --- Events ---
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);

    // --- Core Logic ---

    modifier updateReward(address account) {
        rewardBalance[account] = getPendingRewards(account);
        lastUpdateTime[account] = block.timestamp;
        _;
    }

    /**
     * @notice Stakes amount (Simulated).
     * In production, we would use `transferFrom` or `msg.value`.
     */
    function stake(uint256 amount) external updateReward(msg.sender) {
        stakedBalance[msg.sender] += amount;
        emit Staked(msg.sender, amount);
    }

    /**
     * @notice Withdraws stake + rewards.
     */
    function withdraw(uint256 amount) external updateReward(msg.sender) {
        require(stakedBalance[msg.sender] >= amount, "Insufficient balance");
        stakedBalance[msg.sender] -= amount;

        // Simulate sending back funds
        emit Withdrawn(msg.sender, amount);
    }

    /**
     * @notice Claims only the rewards.
     */
    function claimRewards() external updateReward(msg.sender) {
        uint256 reward = rewardBalance[msg.sender];
        if (reward > 0) {
            rewardBalance[msg.sender] = 0;
            emit RewardsClaimed(msg.sender, reward);
        }
    }

    // --- View Functions (Frontend Dashboard) ---

    /**
     * @notice Calculates rewards earned based on time elapsed.
     * @return The amount of tokens earned since last update.
     */
    function getPendingRewards(address _user) public view returns (uint256) {
        if (stakedBalance[_user] == 0) {
            return rewardBalance[_user];
        }

        uint256 timeElapsed = block.timestamp - lastUpdateTime[_user];

        // Demo Math: Balance * Seconds * Rate
        // stake 1000, and 10 seconds pass:
        // Reward = 1000 * 10 / 100 = 100 tokens.
        uint256 newRewards = (stakedBalance[_user] * timeElapsed) /
            REWARD_RATE_PER_SECOND;

        return rewardBalance[_user] + newRewards;
    }

    /**
     * @notice Helper for the dashboard to get all data in one call.
     */
    function getPosition(
        address _user
    ) external view returns (uint256 staked, uint256 rewards, uint256 apy) {
        return (stakedBalance[_user], getPendingRewards(_user), 31536000);
    }
}
