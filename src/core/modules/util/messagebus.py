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
import traceback
from core.modules.models import ModuleInput, ModuleOutput, CourierEnvelope
from core.modules.translation import translator


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
        # Store expected types for each subscriber to use with translation layer
        self.subscriber_expected_types: Dict[str, Dict[Callable, str]] = defaultdict(
            dict
        )

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
                # Now we log this as a warning instead of an error since we have translation layer
                self._logger.warning(
                    f"Type mismatch for topic '{topic}': Module '{target_module}' expects "
                    f"'{input_def.type_name}' but topic provides '{registered_type.__name__}' - "
                    f"will attempt automatic translation"
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
        """
        Publish data to a topic with type validation asynchronously.

        This method is designed to be robust against failures in the translation layer.
        If translation fails, the original data is passed through unchanged and a warning
        is logged.
        """
        if topic not in self.subscribers:
            self._logger.debug(f"Publishing to topic '{topic}' with no subscribers")
            return

        # Validate data type if expected type is defined
        expected_type = self.output_types.get(topic)
        if expected_type:
            try:
                if not self._is_instance_of_type(data, expected_type):
                    self._logger.warning(
                        f"Type validation failed: Data published to topic '{topic}' is of type {type(data).__name__}, "
                        f"expected {getattr(expected_type, '__name__', str(expected_type))} - "
                        f"proceeding with delivery but subscribers may not be able to process this data"
                    )
                    # Continue with publishing despite validation failure - subscribers may handle it
            except Exception as e:
                self._logger.warning(
                    f"Error during type validation for topic '{topic}': {e}, proceeding with delivery"
                )
                # Continue with publishing despite validation error

        # Warn if data is empty
        if data is None or (isinstance(data, (list, dict, str)) and len(data) == 0):
            self._logger.debug(f"Empty data published to topic '{topic}'")

        # Create a list to collect coroutines for awaiting
        tasks = []

        try:
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
        except Exception as e:
            self._logger.warning(
                f"Error creating envelope: {e}, using minimal envelope"
            )
            # Create a minimal envelope if the full one fails
            envelope = CourierEnvelope(data=data, topic=topic)

        for subscriber in self.subscribers[topic]:
            try:
                # Default to using the original envelope
                subscriber_envelope = envelope
                was_translated = False

                # Try to get the expected type for this subscriber
                try:
                    subscriber_type = self.subscriber_expected_types.get(topic, {}).get(
                        subscriber
                    )

                    # Check if translation is needed
                    if (
                        subscriber_type
                        and envelope.data_type
                        and subscriber_type != envelope.data_type
                    ):
                        # Create a defensive copy to avoid modifying the original envelope
                        try:
                            subscriber_envelope = CourierEnvelope(
                                data=envelope.data,
                                topic=envelope.topic,
                                source_module=envelope.source_module,
                                timestamp=envelope.timestamp,
                                input_name=envelope.input_name,
                                data_type=envelope.data_type,
                            )

                            # Attempt translation - this should never raise exceptions now
                            subscriber_envelope, was_translated = (
                                translator.translate_envelope(
                                    subscriber_envelope, subscriber_type
                                )
                            )

                            if was_translated:
                                self._logger.debug(
                                    f"Translated data from {envelope.data_type} to {subscriber_type} "
                                    f"for topic '{topic}'"
                                )
                        except Exception as copy_error:
                            # If copying or translation fails, use original envelope
                            self._logger.warning(
                                f"Error preparing subscriber-specific envelope: {copy_error}, "
                                f"falling back to original envelope"
                            )
                            subscriber_envelope = envelope
                except Exception as type_error:
                    # If any error occurs in type lookup/translation setup, use original envelope
                    self._logger.warning(
                        f"Error in translation preparation: {type_error}, "
                        f"falling back to original envelope"
                    )
                    subscriber_envelope = envelope

                # Deliver to subscriber with appropriate error handling
                try:
                    # Check if the subscriber is a coroutine function
                    if inspect.iscoroutinefunction(subscriber):
                        # Add coroutine to tasks list with exception handling
                        async def safe_subscriber_call(sub, env):
                            try:
                                return await sub(env)
                            except Exception as call_error:
                                self._logger.error(
                                    f"Error in async subscriber for topic '{topic}': {call_error}\n"
                                    f"{traceback.format_exc()}"
                                )
                                return None

                        tasks.append(
                            safe_subscriber_call(subscriber, subscriber_envelope)
                        )
                    else:
                        # Handle synchronous subscribers immediately with error catching
                        try:
                            subscriber(subscriber_envelope)
                        except Exception as sync_error:
                            self._logger.error(
                                f"Error in sync subscriber for topic '{topic}': {sync_error}\n"
                                f"{traceback.format_exc()}"
                            )
                except Exception as e:
                    self._logger.error(
                        f"Critical error delivering to subscriber: {e}\n"
                        f"{traceback.format_exc()}"
                    )
            except Exception as e:
                # This is a catch-all for any errors in the entire subscriber handling block
                self._logger.error(
                    f"Unexpected error handling subscriber for topic '{topic}': {e}\n"
                    f"{traceback.format_exc()}"
                )

        # Wait for all async subscriber tasks to complete with error handling
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                self._logger.error(f"Error gathering async tasks: {e}")

    def subscribe(
        self,
        topic: str,
        callback: Union[Callable, Awaitable],
        expected_type: Optional[Type] = None,
    ) -> None:
        """Subscribe a callback to a topic with optional type validation."""
        self.subscribers[topic].append(callback)

        # Store the expected type for this subscriber for use with translation
        if expected_type:
            expected_type_name = getattr(expected_type, "__name__", str(expected_type))
            self.subscriber_expected_types[topic][callback] = expected_type_name

            # Check for type mismatches but now as warnings since we can translate
            if topic in self.output_types and self.output_types[topic] != expected_type:
                if self.output_types[topic] != Any and expected_type != Any:
                    output_type_name = getattr(
                        self.output_types[topic],
                        "__name__",
                        str(self.output_types[topic]),
                    )

                    # Check if translation is possible for this type mismatch
                    if translator.can_convert(output_type_name, expected_type_name):
                        self._logger.info(
                            f"Type translation will be applied for topic '{topic}': Publisher provides "
                            f"{output_type_name} but subscriber expects {expected_type_name}"
                        )
                    else:
                        self._logger.warning(
                            f"Type mismatch for topic '{topic}': Subscriber expects "
                            f"{expected_type_name} but topic was registered with "
                            f"{output_type_name} - no translation rule available"
                        )
            else:
                self.output_types[topic] = expected_type
