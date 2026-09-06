from __future__ import annotations

from web3 import Web3
from web3.contract import Contract

ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "attest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "verify",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"},
            {"internalType": "uint64", "name": "", "type": "uint64"},
            {"internalType": "address", "name": "", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class BlockchainRegistry:
    def __init__(self, rpc_url: str, private_key: str, contract_address: str):
        if not rpc_url or not private_key or not contract_address:
            raise ValueError("BASE_SEPOLIA_RPC_URL, BLOCKCHAIN_PRIVATE_KEY and EVIDENCE_REGISTRY_ADDRESS are required")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError("Blockchain RPC is unavailable")
        self.account = self.w3.eth.account.from_key(private_key)
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=ABI
        )

    def attest(self, evidence_hash_hex: str) -> str:
        digest = bytes.fromhex(evidence_hash_hex)
        tx = self.contract.functions.attest(digest).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.w3.eth.chain_id,
                "gas": 150_000,
                "maxFeePerGas": self.w3.to_wei("0.1", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("0.01", "gwei"),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def verify(self, evidence_hash_hex: str) -> dict:
        exists, timestamp, submitter = self.contract.functions.verify(bytes.fromhex(evidence_hash_hex)).call()
        return {"exists": bool(exists), "timestamp": int(timestamp), "submitter": submitter}
