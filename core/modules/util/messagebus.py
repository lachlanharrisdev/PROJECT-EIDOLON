from collections import defaultdict
from typing import Dict, List, Any

import logging


class MessageBus:
    def __init__(self):
        self.subscribers: Dict[str, List] = defaultdict(list)
        self.output_types: Dict[str, type] = {}  # Track expected types for outputs
        self._logger = logging.getLogger(__name__)

    def publish(self, topic: str, data: Any):
        """Publish data to a topic."""
        if topic not in self.subscribers:
            raise ValueError(f"No subscribers for topic: {topic}")

        # Validate data type if expected type is defined
        expected_type = self.output_types.get(topic)
        if expected_type and not isinstance(data, expected_type):
            raise TypeError(
                f"Data published to topic '{topic}' is of type {type(data).__name__}, "
                f"expected {expected_type.__name__}"
            )

        # Warn if data is empty
        if data is None or (isinstance(data, (list, dict, str)) and len(data) == 0):
            self._logger.warning(f"Warning: Empty data published to topic '{topic}'")

        for subscriber in self.subscribers[topic]:
            subscriber(data)

    def subscribe(self, topic: str, callback, expected_type: type = None):
        """Subscribe a callback to a topic."""
        self.subscribers[topic].append(callback)
        if expected_type:
            if topic in self.output_types and self.output_types[topic] != expected_type:
                raise ValueError(
                    f"Conflicting types for topic '{topic}': "
                    f"{self.output_types[topic].__name__} vs {expected_type.__name__}"
                )
            self.output_types[topic] = expected_type
