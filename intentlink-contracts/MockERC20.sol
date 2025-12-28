// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockToken
 * @dev A standard ERC20 token with a public mint function for testing.
 * Used to simulate USDT, USDC, or Wrapped BDAG.
 */
contract MockToken is ERC20 {
    constructor(string memory name, string memory symbol) ERC20(name, symbol) {
        // Mint 1 Million tokens to the deployer initially
        _mint(msg.sender, 1_000_000 * 10 ** decimals());
    }

    /**
     * @notice Free faucet for everyone!
     * @param to The address to receive tokens
     * @param amount The amount (in wei, so 1 = 1e-18)
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
