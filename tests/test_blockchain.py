"""
Unit tests for the real Sepolia gateway WITHOUT internet.

httpx.MockTransport lets us fake the blockchain node's answers. This is
possible only because SepoliaGateway receives its HTTP client from outside
(Dependency Injection) - a nice practical benefit of SOLID.
"""
import json

import httpx

from app.blockchain.base import TxStatus
from app.blockchain.sepolia import SepoliaGateway

TO = "0x1111111111111111111111111111111111111111"
PAYER = "0x2222222222222222222222222222222222222222"
TX = "0x" + "ab" * 32
AMOUNT = 10**15  # 0.001 ETH


def make_gateway(tx=None, receipt=None, block="0x10", fail=False):
    def handler(request: httpx.Request):
        if fail:
            raise httpx.ConnectError("node is down")
        method = json.loads(request.content)["method"]
        result = {"eth_getTransactionByHash": tx,
                  "eth_getTransactionReceipt": receipt,
                  "eth_blockNumber": block}[method]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SepoliaGateway("https://fake-node", min_confirmations=2, http_client=client)


def tx_data(to=TO, value=AMOUNT):
    return {"from": PAYER, "to": to, "value": hex(value)}


def ok_receipt(block="0x0f", status="0x1"):
    return {"status": status, "blockNumber": block}


def test_confirmed_transaction():
    gw = make_gateway(tx_data(), ok_receipt("0x0f"), block="0x10")   # 2 confirmations
    result = gw.verify_transaction(TX, TO, AMOUNT)
    assert result.status == TxStatus.CONFIRMED
    assert result.payer_address == PAYER and result.confirmations == 2


def test_not_enough_confirmations_is_pending():
    gw = make_gateway(tx_data(), ok_receipt("0x10"), block="0x10")   # 1 confirmation
    assert gw.verify_transaction(TX, TO, AMOUNT).status == TxStatus.PENDING


def test_unknown_transaction_is_pending():
    assert make_gateway(tx=None).verify_transaction(TX, TO, AMOUNT).status == TxStatus.PENDING


def test_not_mined_yet_is_pending():
    gw = make_gateway(tx_data(), receipt=None)
    assert gw.verify_transaction(TX, TO, AMOUNT).status == TxStatus.PENDING


def test_wrong_receiver_fails():
    gw = make_gateway(tx_data(to=PAYER), ok_receipt())
    result = gw.verify_transaction(TX, TO, AMOUNT)
    assert result.status == TxStatus.FAILED and "different address" in result.reason


def test_address_comparison_ignores_case():
    gw = make_gateway(tx_data(to=TO.upper().replace("0X", "0x")), ok_receipt(), block="0x10")
    assert gw.verify_transaction(TX, TO, AMOUNT).status == TxStatus.CONFIRMED


def test_too_little_money_fails():
    gw = make_gateway(tx_data(value=AMOUNT - 1), ok_receipt())
    assert gw.verify_transaction(TX, TO, AMOUNT).status == TxStatus.FAILED


def test_reverted_transaction_fails():
    gw = make_gateway(tx_data(), ok_receipt(status="0x0"))
    assert gw.verify_transaction(TX, TO, AMOUNT).status == TxStatus.FAILED


def test_node_down_keeps_payment_pending():
    result = make_gateway(fail=True).verify_transaction(TX, TO, AMOUNT)
    assert result.status == TxStatus.PENDING and "unavailable" in result.reason
