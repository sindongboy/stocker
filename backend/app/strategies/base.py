from dataclasses import dataclass
from typing import Protocol


@dataclass
class Signal:
    ticker: str
    side: str          # "buy" | "sell"
    qty: int
    price: int
    strategy: str
    reasoning: str


class Strategy(Protocol):
    name: str

    async def generate_signal(
        self,
        ticker: str,
        closes: list[int],
        snapshot: dict,
        portfolio: dict,
    ) -> Signal | None: ...
