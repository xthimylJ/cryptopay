"""
The abstraction every blockchain gateway must follow.

This is the heart of the SOLID design:
- PaymentService depends on THIS abstract class, not on Sepolia or the mock
  (Dependency Inversion Principle).
- To support a new network (Tron, Bitcoin, TON...) we ADD a new subclass;
  PaymentService does not change at all (Open/Closed Principle).
- Any subclass can replace any other without breaking the service
  (Liskov Substitution Principle).
- The interface is tiny - one method - so implementers are not forced to
  write methods they don't need (Interface Segregation Principle).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class TxStatus(str, Enum):
    PENDING = "pending"      # not found yet / not enough confirmations
    CONFIRMED = "confirmed"  # valid and final
    FAILED = "failed"        # invalid: wrong receiver, too little money, reverted


@dataclass
class VerificationResult:
    status: TxStatus
    reason: str | None = None
    payer_address: str | None = None
    confirmations: int = 0


class BlockchainGateway(ABC):
    """Checks whether a blockchain transaction correctly pays a payment."""

    network_name: str
    chain_id: int

    @abstractmethod
    def verify_transaction(
        self, tx_hash: str, expected_to: str, expected_amount_wei: int
    ) -> VerificationResult:
        """
        Look up the transaction and decide whether it sent at least
        `expected_amount_wei` to `expected_to`, successfully.
        """
