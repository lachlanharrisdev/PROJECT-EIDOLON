"""Engine module for Project Eidolon"""

# Only import the engine_contract items here to avoid circular imports
from core.modules.engine.engine_contract import IModuleRegistry, ModuleCore
from core.modules.engine.engine_core import ModuleEngine
from core.modules.util.messagebus import MessageBus

__all__ = ["ModuleCore", "IModuleRegistry", "ModuleEngine", "MessageBus"]
