from dataclasses import dataclass
from typing import List, Optional


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
class ModuleConfig:
    name: str
    alias: str
    creator: str
    runtime: ModuleRunTimeOption
    repository: str
    description: str
    version: str
    requirements: Optional[List[DependencyModule]]


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


@dataclass
class Pipeline:
    name: str
    modules: List[PipelineModule]
