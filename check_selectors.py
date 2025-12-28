from web3 import Web3
print(f"stakeFor: {Web3.keccak(text='stakeFor(address,uint256)').hex()[:10]}")
print(f"transferFrom: {Web3.keccak(text='transferFrom(address,address,uint256)').hex()[:10]}")
print(f"approve: {Web3.keccak(text='approve(address,uint256)').hex()[:10]}")
