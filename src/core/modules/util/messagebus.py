from collections import defaultdict
from typing import (
    Dict,
    List,
    Any,
    Type,
    Callable,
    Optional,
    get_origin,
    get_args,
    Union,
    Awaitable,
)
import asyncio
import inspect
import logging
from core.modules.models import ModuleInput, ModuleOutput, CourierEnvelope


class MessageBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Union[Callable, Awaitable]]] = defaultdict(
            list
        )
        self.output_types: Dict[str, Type] = {}  # Track expected types for outputs
        self.topic_sources: Dict[str, str] = (
            {}
        )  # Track which module provides each topic
        self._logger = logging.getLogger(__name__)

    def register_output(
        self, topic: str, output_def: ModuleOutput, source_module: str
    ) -> None:
        """
        Register an output topic with its expected type and source module.

        Args:
            topic: The topic name
            output_def: The ModuleOutput definition
            source_module: The name of the module providing this output
        """
        if topic in self.output_types:
            existing_source = self.topic_sources.get(topic, "unknown")
            if existing_source != source_module:
                self._logger.warning(
                    f"Topic '{topic}' already registered by module '{existing_source}', "
                    f"but is also provided by '{source_module}' - this may cause conflicts"
                )

        python_type = output_def.get_python_type()
        self.output_types[topic] = python_type
        self.topic_sources[topic] = source_module
        self._logger.debug(
            f"Registered output topic '{topic}' with type '{output_def.type_name}' from module '{source_module}'"
        )

    def register_input(
        self, topic: str, input_def: ModuleInput, target_module: str
    ) -> None:
        """
        Register a module's interest in an input topic with type validation.

        Args:
            topic: The topic to subscribe to
            input_def: The ModuleInput definition
            target_module: The name of the module requiring this input
        """
        if topic in self.output_types:
            expected_type = input_def.get_python_type()
            registered_type = self.output_types[topic]

            # Check for type compatibility
            if (
                expected_type != Any
                and registered_type != Any
                and expected_type != registered_type
            ):
                self._logger.error(
                    f"Type mismatch for topic '{topic}': Module '{target_module}' expects "
                    f"'{input_def.type_name}' but topic provides '{registered_type.__name__}' - "
                    f"this will likely cause errors during execution"
                )
        else:
            self._logger.warning(
                f"Module '{target_module}' subscribes to topic '{topic}' that has not been registered as an output"
            )

    def _is_instance_of_type(self, data: Any, expected_type: Type) -> bool:
        """
        Safely check if data is an instance of the expected type,
        handling special types like Any, List[X], Dict[X, Y], etc.

        Args:
            data: The data to check
            expected_type: The expected type

        Returns:
            bool: True if data is of the expected type, False otherwise
        """
        if expected_type is Any:
            return True

        # Handle generic types like List[X], Dict[X, Y]
        origin = get_origin(expected_type)
        if origin is not None:
            # It's a generic type like List[str], Dict[str, int]
            if isinstance(data, origin):
                # For now, we don't validate the inner types
                return True
            return False

        # Regular type check
        return isinstance(data, expected_type)

    async def publish(self, topic: str, data: Any) -> None:
        """Publish data to a topic with type validation asynchronously."""
        if topic not in self.subscribers:
            self._logger.debug(f"Publishing to topic '{topic}' with no subscribers")
            return

        # Validate data type if expected type is defined
        expected_type = self.output_types.get(topic)
        if expected_type:
            try:
                if not self._is_instance_of_type(data, expected_type):
                    self._logger.error(
                        f"Type validation failed: Data published to topic '{topic}' is of type {type(data).__name__}, "
                        f"expected {getattr(expected_type, '__name__', str(expected_type))} - "
                        f"subscribers may not be able to process this data"
                    )
                    # Don't raise to avoid crashing the system, but log the error
                    return
            except Exception as e:
                self._logger.error(
                    f"Error during type validation for topic '{topic}': {e}"
                )
                # Continue with publishing despite validation error

        # Warn if data is empty
        if data is None or (isinstance(data, (list, dict, str)) and len(data) == 0):
            self._logger.debug(f"Empty data published to topic '{topic}'")

        # Create a list to collect coroutines for awaiting
        tasks = []

        # Wrap the data in a CourierEnvelope
        source_module = self.topic_sources.get(topic, None)
        data_type = (
            getattr(expected_type, "__name__", str(expected_type))
            if expected_type
            else None
        )
        envelope = CourierEnvelope(
            data=data, topic=topic, source_module=source_module, data_type=data_type
        )

        for subscriber in self.subscribers[topic]:
            try:
                # Check if the subscriber is a coroutine function
                if inspect.iscoroutinefunction(subscriber):
                    # Add coroutine to tasks list
                    tasks.append(subscriber(envelope))
                else:
                    # Handle synchronous subscribers immediately
                    subscriber(envelope)
            except Exception as e:
                self._logger.error(f"Error in subscriber for topic '{topic}': {e}")

        # Wait for all async subscriber tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(
        self,
        topic: str,
        callback: Union[Callable, Awaitable],
        expected_type: Optional[Type] = None,
    ) -> None:
        """Subscribe a callback to a topic with optional type validation."""
        self.subscribers[topic].append(callback)

        # Add or validate type information
        if expected_type:
            if topic in self.output_types and self.output_types[topic] != expected_type:
                if self.output_types[topic] != Any and expected_type != Any:
                    self._logger.error(
                        f"Type mismatch for topic '{topic}': Subscriber expects "
                        f"{getattr(expected_type, '__name__', str(expected_type))} but topic was registered with "
                        f"{getattr(self.output_types[topic], '__name__', str(self.output_types[topic]))} - "
                        f"this will likely cause errors during runtime"
                    )
            else:
                self.output_types[topic] = expected_type
