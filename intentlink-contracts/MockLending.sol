// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockLending {
    mapping(address => uint256) public deposits;

    event Deposited(address indexed user, uint256 amount);

    /**
     * @notice Simulates depositing an amount for a user.
     */
    function deposit(uint256 amount) external {
        deposits[msg.sender] += amount;
        emit Deposited(msg.sender, amount);
    }
}
