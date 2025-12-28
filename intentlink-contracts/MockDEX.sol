// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockDEX {
    event Swapped(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn
    );

    /**
     * @notice Simulates a swap. In a real DEX, this would handle token transfers.
     */
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external {
        // No actual logic needed for the demo, just a successful call.
        emit Swapped(tokenIn, tokenOut, amountIn);
    }
}
