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
        if self._shutdown_event.is_set():
            self._logger.warning("Force shutting down the application...")
            sys.exit(1)  # Force exit with non-zero code
        else:
            self._logger.info("Shutdown initiated. Press Ctrl+C again to force quit.")
            self._shutdown_event.set()
            # We don't need to create a separate task here, just set the shutdown event
            # The main event loop will handle the shutdown process

    def trigger_shutdown(self):
        """
        Trigger the shutdown event to start the graceful shutdown process.
        """
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
            self._logger.warning("No modules registered for shutdown")
            return
            
        self._logger.info("Shutting down modules...")
        for module in self._modules:
            try:
                self._logger.info(f"Shutting down module: {module}")
                await module.shutdown()
            except Exception as e:
                self._logger.error(f"Error shutting down module {module}: {e}")

    async def shutdown_application(self):
        """
        Perform the full application shutdown process.
        This method should be awaited from the main application to ensure proper shutdown.
        """
        self._logger.info("Application shutdown initiated.")
        await self.shutdown_modules()
        self._logger.info("Application shutdown complete.")
        # We won't call sys.exit() or loop.stop() here
        # Let the caller handle the termination of the application
