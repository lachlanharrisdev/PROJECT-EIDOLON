import asyncio
import signal
import sys
from logging import Logger


class ShutdownCoordinator:
    def __init__(self, logger: Logger):
        """
        Initialize the ShutdownCoordinator with a logger.
        """
        self._logger = logger
        self._shutdown_event = asyncio.Event()
        self._force_shutdown = False
        self._modules = None  # To store the modules for shutdown

    def register_signal_handlers(self, modules):
        """
        Register signal handlers for graceful and forced shutdowns.
        """
        self._modules = modules
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, signum, frame):
        """
        Handle SIGINT (Ctrl+C) for graceful and forced shutdowns.
        """
        if self._force_shutdown:
            self._logger.critical("Forced shutdown initiated. Exiting immediately.")
            sys.exit(1)
        else:
            self._logger.warning(
                "Graceful shutdown initiated. Press Ctrl+C again to force exit."
            )
            self._force_shutdown = True
            self.trigger_shutdown()

    def trigger_shutdown(self):
        """
        Trigger the shutdown event to start the graceful shutdown process.
        """
        self._logger.debug("Shutdown event triggered")
        self._shutdown_event.set()

    async def wait_for_shutdown(self):
        """
        Wait for the shutdown event to be triggered.
        """
        await self._shutdown_event.wait()

    async def shutdown_modules(self):
        """
        Gracefully shut down all running modules.
        """
        if not self._modules:
            self._logger.debug("No modules to shut down")
            return

        self._logger.info("Shutting down modules...")
        shutdown_coroutines = []

        for module in self._modules:
            try:
                # Check if module has a shutdown method
                if hasattr(module, "shutdown") and callable(module.shutdown):
                    self._logger.debug(
                        f"Initiating shutdown for module: {module.meta.name}"
                    )
                    shutdown_coroutines.append(module.shutdown())
                else:
                    self._logger.debug(
                        f"Module {module} does not have a shutdown method"
                    )
            except Exception as e:
                self._logger.warning(f"Error preparing shutdown for module: {e}")

        if shutdown_coroutines:
            try:
                # Wait for all modules to shut down with a timeout
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_coroutines, return_exceptions=True),
                    timeout=10,
                )
                self._logger.debug("All modules shutdown complete")
            except asyncio.TimeoutError:
                self._logger.warning(
                    "Timeout while waiting for module shutdowns - some modules may not have shut down cleanly"
                )
            except Exception as e:
                self._logger.error(f"Error during module shutdown: {e}")

    async def shutdown_application(self):
        """
        Shut down the entire application gracefully.
        """
        self._logger.info("Application shutdown process initiated")

        try:
            # First shut down all modules
            await self.shutdown_modules()

            self._logger.debug("Application shutdown completed successfully")
        except Exception as e:
            self._logger.error(f"Error during application shutdown: {e}")

        return True
