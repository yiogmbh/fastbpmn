from typing import Protocol

from .models import Signal, SignalResult, Message, MessageResult, MessageFailure


class SignalEmitter(Protocol):
    async def __call__(self, signal: Signal) -> SignalResult:
        pass


class MessageCorrelator(Protocol):
    async def __call__(self, message: Message) -> MessageResult | MessageFailure:
        pass
