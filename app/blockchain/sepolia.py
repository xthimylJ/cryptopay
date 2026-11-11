"""
Real integration with the Ethereum Sepolia test network.

We talk to an Ethereum node through JSON-RPC - a simple protocol where we
POST a JSON like {"method": "eth_getTransactionByHash", "params": [...]}
and get JSON back. No crypto library is needed for reading the chain.

Three RPC calls are used:
  eth_getTransactionByHash   -> who sent, to whom, how much
  eth_getTransactionReceipt  -> was it included in a block, did it succeed
  eth_blockNumber            -> current block, to count confirmations
"""
import httpx

from app.blockchain.base import BlockchainGateway, TxStatus, VerificationResult
from app.config import SEPOLIA_CHAIN_ID


class RpcError(Exception):
    pass


class SepoliaGateway(BlockchainGateway):
    network_name = "sepolia"
    chain_id = SEPOLIA_CHAIN_ID

    def __init__(self, rpc_url: str, min_confirmations: int = 1,
                 http_client: httpx.Client | None = None):
        self.rpc_url = rpc_url
        self.min_confirmations = min_confirmations
        # The client can be injected - tests pass a fake one (Dependency Injection).
        self.http = http_client or httpx.Client(timeout=10)

    def _rpc(self, method: str, params: list):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = self.http.post(self.rpc_url, json=body)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RpcError(data["error"])
        return data.get("result")

    def verify_transaction(self, tx_hash, expected_to, expected_amount_wei):
        try:
            tx = self._rpc("eth_getTransactionByHash", [tx_hash])
            if tx is None:
                # Not visible yet (still propagating) - check again later.
                return VerificationResult(TxStatus.PENDING, "Transaction not found yet")

            payer = tx.get("from")
            to = (tx.get("to") or "").lower()
            value = int(tx.get("value", "0x0"), 16)   # hex string -> int

            # Business checks: right receiver and enough money.
            if to != expected_to.lower():
                return VerificationResult(TxStatus.FAILED,
                                          "Transaction was sent to a different address", payer)
            if value < expected_amount_wei:
                return VerificationResult(TxStatus.FAILED,
                                          "Transaction amount is lower than required", payer)

            receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt is None:
                return VerificationResult(TxStatus.PENDING, "Waiting to be mined", payer)
            if receipt.get("status") != "0x1":
                return VerificationResult(TxStatus.FAILED,
                                          "Transaction reverted on-chain", payer)

            current_block = int(self._rpc("eth_blockNumber", []), 16)
            tx_block = int(receipt["blockNumber"], 16)
            confirmations = current_block - tx_block + 1
            if confirmations < self.min_confirmations:
                return VerificationResult(TxStatus.PENDING, "Waiting for confirmations",
                                          payer, confirmations)

            return VerificationResult(TxStatus.CONFIRMED, None, payer, confirmations)

        except (httpx.HTTPError, RpcError, ValueError, KeyError) as exc:
            # Network problems are temporary: keep the payment waiting
            # instead of failing it. The next check will try again.
            return VerificationResult(TxStatus.PENDING, f"Blockchain node unavailable: {exc}")
