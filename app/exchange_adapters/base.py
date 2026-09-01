from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Balance:
    venue: str
    asset: str
    quantity: float


class ExchangeAdapter(ABC):
    """Four methods only. No order/withdraw/transfer method may be added here —
    see docs/SECURITY.md §1. This boundary is what keeps the system read-only."""

    @abstractmethod
    def get_balances(self) -> list[Balance]:
        ...

    @abstractmethod
    def get_prices(self, assets: list[str]) -> dict[str, float]:
        ...

    @abstractmethod
    def get_key_scopes(self) -> list[str]:
        ...

    @abstractmethod
    def health(self) -> bool:
        ...
