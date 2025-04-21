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
        self.keywords: List[str] = []
        self.processed_keywords: Dict[str, int] = {}

        # Read any arguments from the pipeline
        self.module_args = self.get_arguments()
        self.log(f"Initialized with module arguments: {self.module_args}")

    def process(self, data: Any) -> None:
        """
        Process incoming data from subscribed topics.
        """
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            self.keywords = data
            self._process_keywords()
        else:
            self.log(f"Unexpected data type: {type(data)}", "warning")

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run one iteration of the module's logic.
        """
        # Process any pending keywords and publish results
        if self.keywords and not self.processed_keywords:
            self._process_keywords()

        # Publish processed keywords if available
        if self.processed_keywords:
            self.log(f"Publishing {len(self.processed_keywords)} processed keywords")
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
