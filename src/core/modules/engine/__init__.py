"""Engine module for Project Eidolon"""

# Only import the engine_contract items here to avoid circular imports
from .engine_contract import IModuleRegistry, ModuleCore
from .engine_core import ModuleEngine
from ..util.messagebus import MessageBus

__all__ = ["ModuleCore", "IModuleRegistry", "ModuleEngine", "MessageBus"]
