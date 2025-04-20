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

    def _initialize_module(self) -> None:
        """
        Initialize module-specific components.
        Called after the base ModuleCore initialization.
        """
        self.keywords: List[str] = []
        self.processed_keywords: Dict[str, int] = {}

        # Read any arguments from the pipeline
        self.module_args = self.get_arguments()
        self.log(f"Initialized with module arguments: {self.module_args}")

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        Override of the ModuleCore _process_input method.
        """
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            self.keywords = data
            self._process_keywords()
        else:
            self.log(f"Received unexpected data type: {type(data)}", "warning")

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        Run one iteration of the module's main logic.
        """
        # Process any pending keywords and publish results
        if self.keywords and not self.processed_keywords:
            self._process_keywords()

        # Publish processed keywords if available
        if self.processed_keywords:
            self.log(
                f"Publishing {len(self.processed_keywords)} processed keywords", "info"
            )
            await message_bus.publish("processed_keywords", self.processed_keywords)

    def _process_keywords(self) -> None:
        """
        Process the keywords and assign priority scores.
        Uses weighting from module arguments if available.
        """
        self.processed_keywords = {}

        # Get argument values with defaults if not provided
        base_score = self.get_argument("base_score", 10)
        length_weight = self.get_argument("length_weight", 0.5)

        self.log(
            f"Processing keywords with base_score={base_score}, length_weight={length_weight}",
            "debug",
        )

        for keyword in self.keywords:
            # Simple algorithm: base score + weighted score based on word length
            score = base_score + (len(keyword) * length_weight)
            self.processed_keywords[keyword] = int(score)

        self.log(f"Processed {len(self.processed_keywords)} keywords", "debug")

    def _handle_custom_command(self, command: chr) -> Device:
        """
        Handle custom module commands.
        """
        if command == "C":
            # Example custom command to clear keywords
            self.keywords = []
            return Device(
                name=self.meta.name, firmware=0xB0000, protocol="CUSTOM", errors=[]
            )

        return super()._handle_custom_command(command)
