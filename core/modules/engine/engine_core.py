from logging import Logger

from core.modules.usecase import ModuleUseCase
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus


class ModuleEngine:
    def __init__(self, **args):
        self._logger = LogUtil.create(args["options"]["log_level"])
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
            }
        )
        self.message_bus = MessageBus()

    def start(self):
        self.__reload_modules()
        self.__connect_modules()
        self.__invoke_on_modules()

    def __reload_modules(self):
        """Discover and load all modules."""
        self.use_case.discover_modules(True)

    def __connect_modules(self):
        """Connect modules based on their inputs and outputs."""
        for module in self.use_case.modules:
            self._logger.debug(f"Connecting module: {module} (type: {type(module)})")

            # Correctly call get_config() on the module instance
            config = module.get_config()

            outputs = config.get("outputs", [])
            inputs = config.get("inputs", [])

            # Publish outputs to the message bus
            for output in outputs:
                topic = output["name"]  # Extract the name of the output
                if topic in self.message_bus.subscribers:
                    self._logger.warning(
                        f"Multiple modules are providing the same output: {topic}"
                    )
                self._logger.info(f'{module} set to PUBLISH topic: "{topic}"')

            # Subscribe inputs with types
            for input_item in inputs:
                topic = input_item["name"]  # Extract the name of the input
                self.message_bus.subscribe(topic, module.handle_input)
                self._logger.info(f'{module} subscribed to INPUT topic: "{topic}"')

    def __invoke_on_modules(self):
        """Invoke all modules."""
        for module in self.use_case.modules:
            try:
                module.run(self.message_bus)
            except Exception as e:
                self._logger.error(f"Error running module {module}: {e}")
