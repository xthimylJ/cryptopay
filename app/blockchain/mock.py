"""
Simulated blockchain for demos, offline work and automated tests.

Rules (easy to remember on a demo):
  - any valid transaction hash is CONFIRMED,
  - a hash ending in "0000" is FAILED (to demonstrate the failure path).
"""
from app.blockchain.base import BlockchainGateway, TxStatus, VerificationResult
from app.config import SEPOLIA_CHAIN_ID

MOCK_PAYER = "0x000000000000000000000000000000000000dEaD"


class MockGateway(BlockchainGateway):
    network_name = "sepolia-simulated"
    chain_id = SEPOLIA_CHAIN_ID

    def verify_transaction(self, tx_hash, expected_to, expected_amount_wei):
        if tx_hash.endswith("0000"):
            return VerificationResult(TxStatus.FAILED,
                                      "Simulated failure (hash ends with 0000)", MOCK_PAYER)
        return VerificationResult(TxStatus.CONFIRMED, None, MOCK_PAYER, confirmations=1)
