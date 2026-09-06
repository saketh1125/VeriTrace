"""Compile/deploy EvidenceRegistry using py-solc-x + Web3.

Set BASE_SEPOLIA_RPC_URL and BLOCKCHAIN_PRIVATE_KEY in the environment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from solcx import compile_standard, install_solc
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "contracts" / "EvidenceRegistry.sol").read_text()


def main() -> None:
    rpc = os.environ["BASE_SEPOLIA_RPC_URL"]
    private_key = os.environ["BLOCKCHAIN_PRIVATE_KEY"]
    install_solc("0.8.24")
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"EvidenceRegistry.sol": {"content": SOURCE}},
            "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
        },
        solc_version="0.8.24",
    )
    artifact = compiled["contracts"]["EvidenceRegistry.sol"]["EvidenceRegistry"]
    w3 = Web3(Web3.HTTPProvider(rpc))
    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["evm"]["bytecode"]["object"])
    tx = contract.constructor().build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": w3.eth.chain_id,
            "gas": 500_000,
            "maxFeePerGas": w3.to_wei("0.1", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("0.01", "gwei"),
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(json.dumps({"contract": getattr(receipt, "contractAddress", None), "tx_hash": tx_hash.hex()}, indent=2))


if __name__ == "__main__":
    main()
