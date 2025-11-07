// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "hardhat/console.sol";

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract IntentWallet is Ownable, Pausable, ReentrancyGuard, EIP712 {
    struct Plan {
        bytes32 planId;
        bytes32 planHash;
        uint256 nonce;
        uint256 expiry;
    }
    mapping(address => uint256) public nonces;
    mapping(address => bool) public isTargetWhitelisted;
    mapping(address => bool) public isRelayerAuthorized;
    bytes32 private constant _PLAN_TYPEHASH =
        keccak256(
            "Plan(bytes32 planId,bytes32 planHash,uint256 nonce,uint256 expiry)"
        );
    event IntentExecuted(
        address indexed user,
        bytes32 indexed planId,
        bytes32 cidHash,
        address indexed relayer,
        uint256 nonce
    );
    event TargetWhitelistUpdated(address indexed target, bool isAllowed);
    event RelayerAuthorizationUpdated(address indexed relayer, bool isAllowed);

    /**
     * @notice Sets up the EIP-712 domain separator and initial owner.
     * @param initialOwner The address to be set as the initial owner of the contract.
     */
    constructor(
        address initialOwner
    ) Ownable(initialOwner) EIP712("IntentLink", "1") {
        // --- DEBUGGING LOGS ---
        console.log("--> IntentWallet constructor executing...");
        console.log("    Deployer (msg.sender):", msg.sender);
        console.log("    Initial Owner parameter:", initialOwner);
        // --- END DEBUGGING LOGS ---
    }

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
        require(signer != address(0), "Invalid signature");
        require(signer == user, "Signer does not match user");
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
