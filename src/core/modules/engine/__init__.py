"""Engine module for Project Eidolon"""

# Only import the engine_contract items here to avoid circular imports
from core.modules.engine.engine_contract import IModuleRegistry, ModuleCore

# The MessageBus and ModuleEngine will be imported directly when needed

__all__ = ["ModuleCore", "IModuleRegistry", "ModuleEngine", "MessageBus"]
