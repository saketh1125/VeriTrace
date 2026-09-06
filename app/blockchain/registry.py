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

BASE_SEPOLIA_CHAIN_ID = 84532


def _hash_bytes(evidence_hash_hex: str) -> bytes:
    if not isinstance(evidence_hash_hex, str) or len(evidence_hash_hex) != 64:
        raise ValueError("INVALID_EVIDENCE_HASH")
    try:
        return bytes.fromhex(evidence_hash_hex)
    except ValueError as exc:
        raise ValueError("INVALID_EVIDENCE_HASH") from exc


class BlockchainRegistry:
    def __init__(self, rpc_url: str, private_key: str, contract_address: str):
        if not rpc_url or not private_key or not contract_address:
            raise ValueError("BASE_SEPOLIA_RPC_URL, BLOCKCHAIN_PRIVATE_KEY and EVIDENCE_REGISTRY_ADDRESS are required")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError("Blockchain RPC is unavailable")
        if self.w3.eth.chain_id != BASE_SEPOLIA_CHAIN_ID:
            raise RuntimeError(f"UNEXPECTED_CHAIN_ID: expected {BASE_SEPOLIA_CHAIN_ID}")
        self.account = self.w3.eth.account.from_key(private_key)
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=ABI
        )

    def attest(self, evidence_hash_hex: str) -> str:
        digest = _hash_bytes(evidence_hash_hex)
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
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if int(receipt["status"]) != 1:
            raise RuntimeError("ATTESTATION_TRANSACTION_FAILED")
        return tx_hash.hex()

    def verify(self, evidence_hash_hex: str) -> dict:
        exists, timestamp, submitter = self.contract.functions.verify(_hash_bytes(evidence_hash_hex)).call()
        return {"exists": bool(exists), "timestamp": int(timestamp), "submitter": submitter}
