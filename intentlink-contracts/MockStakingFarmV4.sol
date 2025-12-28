// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract MockStakingFarmV4 {
    using SafeERC20 for IERC20;

    IERC20 public stakingToken;

    mapping(address => uint256) public stakedBalance;
    mapping(address => uint256) public rewardBalance;
    mapping(address => uint256) public lastUpdateTime;
    uint256 public constant REWARD_RATE_PER_SECOND = 100;

    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);

    // Constructor now requires the Token Address
    constructor(address _stakingToken) {
        stakingToken = IERC20(_stakingToken);
    }

    modifier updateReward(address account) {
        rewardBalance[account] = getPendingRewards(account);
        lastUpdateTime[account] = block.timestamp;
        _;
    }

    function stakeFor(
        address onBehalfOf,
        uint256 amount
    ) external updateReward(onBehalfOf) {
        // REAL LOGIC: Pull tokens from the caller (IntentWallet)
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);

        stakedBalance[onBehalfOf] += amount;
        emit Staked(onBehalfOf, amount);
    }

    // Legacy stake for direct interaction
    function stake(uint256 amount) external updateReward(msg.sender) {
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        stakedBalance[msg.sender] += amount;
        emit Staked(msg.sender, amount);
    }

    function withdraw(uint256 amount) external updateReward(msg.sender) {
        require(stakedBalance[msg.sender] >= amount, "Insufficient balance");
        stakedBalance[msg.sender] -= amount;
        // REAL LOGIC: Send tokens back
        stakingToken.safeTransfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function claimRewards() external updateReward(msg.sender) {
        uint256 reward = rewardBalance[msg.sender];
        if (reward > 0) {
            rewardBalance[msg.sender] = 0;
            emit RewardsClaimed(msg.sender, reward);
        }
    }

    function getPendingRewards(address _user) public view returns (uint256) {
        if (stakedBalance[_user] == 0) return rewardBalance[_user];
        uint256 timeElapsed = block.timestamp - lastUpdateTime[_user];
        uint256 newRewards = ((stakedBalance[_user] * timeElapsed) / 1e15) *
            REWARD_RATE_PER_SECOND;
        return rewardBalance[_user] + newRewards;
    }

    function getPosition(
        address _user
    ) external view returns (uint256 staked, uint256 rewards, uint256 apy) {
        return (stakedBalance[_user], getPendingRewards(_user), 31536000);
    }
}
