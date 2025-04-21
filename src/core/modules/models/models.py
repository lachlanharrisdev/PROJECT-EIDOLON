from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Type


@dataclass
class ModuleRunTimeOption(object):
    main: str
    tests: Optional[List[str]]


@dataclass
class DependencyModule:
    name: str
    version: str
    constraint: str = "=="  # Default to exact version matching

    def __str__(self) -> str:
        # Format the dependency as name + constraint + version for pip
        return f"{self.name}{self.constraint}{self.version}"

    @classmethod
    def from_requirement_string(cls, req_string: str):
        """Creates a DependencyModule from a requirement string like 'package>=1.0.0'"""
        import re

        # Match package name and version with constraint
        match = re.match(r"([a-zA-Z0-9_\-\.]+)([>=<~!]+)([0-9a-zA-Z\.\-]+)", req_string)
        if match:
            name, constraint, version = match.groups()
            return cls(name=name, version=version, constraint=constraint)

        # If no constraint found, assume it's just a package name
        return cls(name=req_string, version="", constraint="")


@dataclass
class ModuleInput:
    name: str
    type_name: str  # String representation of type (e.g., "str", "List[dict]", etc.)
    description: Optional[str] = None
    source: Optional[str] = (
        None  # Optional source module.output_name for pipeline connections
    )

    def get_python_type(self) -> Type:
        """Convert the string representation to an actual Python type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "any": Any,
            "List[str]": List[str],
            "List[dict]": List[dict],
            "Dict[str, Any]": Dict[str, Any],
        }
        return type_mapping.get(self.type_name.lower(), Any)

    # TODO: build this in a way that's non-hardcoded


@dataclass
class ModuleOutput:
    name: str
    type_name: str  # String representation of type
    description: Optional[str] = None

    def get_python_type(self) -> Type:
        """Convert the string representation to an actual Python type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "any": Any,
            "List[str]": List[str],
            "List[dict]": List[dict],
            "Dict[str, Any]": Dict[str, Any],
        }
        return type_mapping.get(self.type_name.lower(), Any)


@dataclass
class ModuleConfig:
    name: str
    alias: str
    creator: str
    runtime: ModuleRunTimeOption
    repository: str
    description: str
    version: str
    requirements: Optional[List[DependencyModule]] = None
    inputs: Optional[List[ModuleInput]] = None
    outputs: Optional[List[ModuleOutput]] = None


@dataclass
class Meta:
    name: str
    description: str
    version: str

    def __str__(self) -> str:
        return f"{self.name}: {self.version}"


@dataclass
class Device:
    name: str
    firmware: int
    protocol: str
    errors: List[int]


@dataclass
class PipelineExecution:
    """Configuration for pipeline execution"""

    timeout: Optional[str] = None
    max_threads: int = 4


@dataclass
class PipelineModule:
    """Represents a module in a pipeline configuration"""

    # Required fields
    name: str  # Will come from the 'module' field

    # New fields
    id: Optional[str] = None  # How this module is identified within the pipeline
    depends_on: Optional[List[str]] = None  # List of module IDs this depends on
    input_mappings: Optional[Dict[str, str]] = None  # Maps input_name -> output_name
    config: Optional[Dict[str, Any]] = None  # Module-specific configuration
    outputs: Optional[List[Dict[str, str]]] = None  # Output mappings
    run_mode: Optional[str] = None  # loop, once, on_trigger, reactive

    def get_id(self) -> str:
        """Get the ID used to reference this module"""
        return self.id if self.id else self.name


@dataclass
class Pipeline:
    """
    Represents a pipeline configuration.
    A pipeline contains modules with specific execution order, input/output mappings,
    and execution settings.
    """

    name: str
    description: Optional[str] = field(default=None)
    modules: List[PipelineModule] = field(default_factory=list)
    execution: PipelineExecution = field(default_factory=PipelineExecution)
