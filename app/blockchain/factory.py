"""
Factory: decides WHICH gateway to create, based on configuration.

This is the only place in the program that knows the concrete classes.
Everyone else receives a `BlockchainGateway` and works with it.
"""
from functools import lru_cache

from app.blockchain.base import BlockchainGateway
from app.blockchain.mock import MockGateway
from app.blockchain.sepolia import SepoliaGateway
from app.config import settings


@lru_cache  # create the gateway once and reuse it
def get_blockchain_gateway() -> BlockchainGateway:
    if settings.BLOCKCHAIN_MODE == "sepolia":
        return SepoliaGateway(settings.SEPOLIA_RPC_URL, settings.MIN_CONFIRMATIONS)
    return MockGateway()
