from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Type


@dataclass
class ModuleRunTimeOption(object):
    main: str
    tests: Optional[List[str]]


@dataclass
class DependencyModule:
    name: str
    version: str

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


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
class PipelineModuleDependency:
    name: str


@dataclass
class PipelineModule:
    name: str
    depends_on: Optional[List[str]] = None
    input_mappings: Optional[Dict[str, str]] = (
        None  # Maps input_name -> dependency.output_name
    )


@dataclass
class Pipeline:
    name: str
    modules: List[PipelineModule]
