from logging import Logger
from typing import List, Dict, Any

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus


class KeywordPrinterModule(ModuleCore):
    """
    Simple module that receives keywords and prints them to the console.
    Demonstrates the use of the enhanced ModuleCore functionality.
    """

    def _initialize_module(self) -> None:
        """
        Initialize module-specific components.
        """
        self.keywords = {}
        self._logger.info(
            "KeywordPrinter module initialized and ready to receive keywords"
        )

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        """
        # Make sure we clearly log when we receive data to help with debugging
        self._logger.info(f"Received data of type: {type(data).__name__}")

        if isinstance(data, dict):
            self.keywords = data
            self._logger.info(
                f"\nKeyword printer received {len(data)} keywords: \n{data}\n"
            )
        else:
            self._logger.error(
                f"Received data of unexpected type: {type(data).__name__}"
            )

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        A single iteration of the module's main logic.
        """
        if self.keywords:
            self._logger.info(f"Currently tracking {len(self.keywords)} keywords")

    def _get_cycle_time(self) -> float:
        """
        Get the time between execution cycles.
        """
        return 15.0  # Run every 15 seconds

    def _get_status(self) -> Device:
        """
        Get the current status of the module.
        """
        return Device(
            name=self.meta.name, firmware=0xA2C3F, protocol="PRINTER", errors=[]
        )
