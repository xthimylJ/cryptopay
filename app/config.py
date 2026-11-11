"""
Application configuration.

All settings come from environment variables, so the same code runs
locally (SQLite, mock blockchain) and on Render (PostgreSQL, Sepolia testnet)
without any code changes. This follows the "Twelve-Factor App" principle:
configuration lives in the environment, not in the code.
"""
import os


class Settings:
    # Database. Locally we use a SQLite file; on Render this is set to the
    # PostgreSQL connection string automatically (see render.yaml).
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cryptopay.db")

    # Which blockchain gateway to use:
    #   "sepolia" - real Ethereum Sepolia testnet (free test ETH, MetaMask)
    #   "mock"    - simulated blockchain, works offline (for demos and tests)
    BLOCKCHAIN_MODE: str = os.getenv("BLOCKCHAIN_MODE", "mock").lower()

    # Public JSON-RPC endpoint of the Sepolia network (no account needed).
    SEPOLIA_RPC_URL: str = os.getenv(
        "SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com"
    )

    # How many blocks must be built on top of the transaction's block before
    # we treat the payment as final. 1 is enough for a testnet demo.
    MIN_CONFIRMATIONS: int = int(os.getenv("MIN_CONFIRMATIONS", "1"))

    # How long a customer has to pay before the payment expires.
    PAYMENT_TTL_MINUTES: int = int(os.getenv("PAYMENT_TTL_MINUTES", "30"))

    # Public base URL of the service, used to build checkout links.
    # On Render, RENDER_EXTERNAL_URL is provided automatically.
    BASE_URL: str = os.getenv(
        "BASE_URL", os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    ).rstrip("/")


settings = Settings()

# Sepolia chain id: 11155111 in decimal = 0xaa36a7 in hex.
SEPOLIA_CHAIN_ID = 11155111
