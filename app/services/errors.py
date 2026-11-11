"""
Business (domain) errors.

Services raise these instead of HTTP errors, because services should not
know anything about HTTP - they could be reused from a CLI or a worker.
main.py translates them into HTTP status codes (404, 409, 400).
"""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class InvalidStateError(DomainError):
    status_code = 400
