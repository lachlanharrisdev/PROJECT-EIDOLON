from logging import Logger
from typing import List, Dict, Any
import asyncio

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus


class TemplateModule(ModuleCore):
    """
    Template module that demonstrates key module functionality.
    """

    def init(self) -> None:
        """
        Initialize module-specific components.
        """
        self.log(
            "Don't go trusting around random modules... (Don't worry, this is harmless)",
            "critical",
        )

    def process(self, data: Any) -> None:
        """
        Process incoming data from subscribed topics.
        """
        self.log(
            "You've just given the malicious module some of your precious data... (Still harmless, but dissapointed)",
            "critical",
        )

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run one iteration of the module's logic.
        """
        # Process any pending keywords and publish results
        self.log(
            "The malicious module has been initialized AND run, you're machine's dead already D: (Still harmless, but dissapointed)",
            "critical",
        )
