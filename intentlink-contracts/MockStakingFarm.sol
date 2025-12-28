// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockStakingFarm {
    mapping(address => uint256) public balances;

    event Staked(address indexed user, uint256 amount);

    /**
     * @notice Simulates staking an amount for a user.
     * In a real farm, this would likely involve an ERC20 transferFrom.
     * For this mock, we just update an internal balance.
     */
    function stake(uint256 amount) external {
        balances[msg.sender] += amount;
        emit Staked(msg.sender, amount);
    }
}
