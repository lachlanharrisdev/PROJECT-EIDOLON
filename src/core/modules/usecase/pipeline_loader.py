import os
import logging
import yaml
from typing import Optional, Dict, List

from dacite import (
    from_dict,
    ForwardReferenceError,
    UnexpectedDataError,
    WrongTypeError,
    MissingValueError,
)

from core.modules.models import Pipeline, PipelineModule
from core.modules.util import FileSystem


class PipelineLoader:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def load_pipeline(self, pipeline_name: str) -> Optional[Pipeline]:
        """
        Load a pipeline configuration by name.
        If a file extension is provided, it will be used as-is, otherwise .yaml is appended.

        :param pipeline_name: The name of the pipeline to load (with or without .yaml extension)
        :return: A Pipeline object if successful, None otherwise
        """
        pipeline_path = self._get_pipeline_path(pipeline_name)
        if not pipeline_path:
            return None

        return self._parse_pipeline_file(pipeline_path)

    def _get_pipeline_path(self, pipeline_name: str) -> Optional[str]:
        """
        Determine the full path to a pipeline configuration file.

        :param pipeline_name: The name of the pipeline (with or without extension)
        :return: The absolute path to the pipeline file, or None if it doesn't exist
        """
        pipelines_dir = FileSystem.get_pipelines_directory()

        # If no extension is provided, append .yaml
        if not any(pipeline_name.endswith(ext) for ext in [".yaml", ".yml"]):
            pipeline_file = f"{pipeline_name}.yaml"
        else:
            pipeline_file = pipeline_name

        pipeline_path = os.path.join(pipelines_dir, pipeline_file)

        if not os.path.isfile(pipeline_path):
            self._logger.error(f"Pipeline file not found: {pipeline_path}")
            return None

        return pipeline_path

    def _parse_pipeline_file(self, pipeline_path: str) -> Optional[Pipeline]:
        """
        Parse a pipeline YAML file and convert it to a Pipeline object.

        :param pipeline_path: The absolute path to the pipeline YAML file
        :return: A Pipeline object if successful, None otherwise
        """
        try:
            with open(pipeline_path, "r") as file:
                pipeline_data = yaml.safe_load(file)

            if not pipeline_data:
                self._logger.error(f"Empty or invalid pipeline file: {pipeline_path}")
                return None

            # Ensure pipeline_data has required fields
            if "name" not in pipeline_data:
                self._logger.error(
                    f"Pipeline file missing required 'name' field: {pipeline_path}"
                )
                return None

            if "modules" not in pipeline_data or not isinstance(
                pipeline_data["modules"], list
            ):
                self._logger.error(
                    f"Pipeline file missing required 'modules' list: {pipeline_path}"
                )
                return None

            # Fix potential YAML parsing issues with the depends_on field
            # The issue in the provided default.yaml has a misplaced hyphen: -depends_on
            self._fix_module_depends_on(pipeline_data)

            # Convert to Pipeline object
            pipeline = from_dict(data_class=Pipeline, data=pipeline_data)
            self._logger.info(
                f"Successfully loaded pipeline '{pipeline.name}' with {len(pipeline.modules)} modules"
            )
            return pipeline

        except FileNotFoundError:
            self._logger.error(f"Pipeline file not found: {pipeline_path}")
        except yaml.YAMLError as e:
            self._logger.error(
                f"Error parsing YAML in pipeline file {pipeline_path}: {e}"
            )
        except (
            ForwardReferenceError,
            UnexpectedDataError,
            WrongTypeError,
            MissingValueError,
        ) as e:
            self._logger.error(
                f"Error converting pipeline data to Pipeline object: {e}"
            )
        except Exception as e:
            self._logger.error(
                f"Unexpected error loading pipeline file {pipeline_path}: {e}"
            )

        return None

    def _fix_module_depends_on(self, pipeline_data: Dict) -> None:
        """
        Fix potential YAML parsing issues with the depends_on field.
        Sometimes the YAML parser might interpret '-depends_on' as a field name instead of a list item.

        :param pipeline_data: The parsed pipeline data to fix
        """
        if "modules" not in pipeline_data:
            return

        for module in pipeline_data["modules"]:
            if isinstance(module, dict):
                # Check for the error case: -depends_on instead of depends_on
                for key in list(module.keys()):
                    if key.startswith("-"):
                        correct_key = key[1:]  # Remove the leading dash
                        self._logger.warning(
                            f"Found incorrectly formatted key '{key}' in pipeline, fixing to '{correct_key}'"
                        )
                        module[correct_key] = module.pop(key)
