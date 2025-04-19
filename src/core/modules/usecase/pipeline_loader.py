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
                raw_data = yaml.safe_load(file)

            if not raw_data:
                self._logger.error(f"Empty or invalid pipeline file: {pipeline_path}")
                return None

            # Extract pipeline data from the wrapping pipeline object
            if "pipeline" not in raw_data:
                self._logger.error(
                    f"Pipeline file missing required 'pipeline' wrapper: {pipeline_path}"
                )
                return None

            pipeline_data = raw_data["pipeline"]

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

            # Process modules to normalize field formats
            self._normalize_pipeline_modules(pipeline_data)

            # Normalize execution configuration if present
            if "execution" in pipeline_data and isinstance(
                pipeline_data["execution"], dict
            ):
                if "timeout" in pipeline_data["execution"] and isinstance(
                    pipeline_data["execution"]["timeout"], str
                ):
                    timeout = pipeline_data["execution"]["timeout"]
                    self._logger.debug(f"Processing execution timeout: {timeout}")

                if "max_threads" in pipeline_data["execution"] and isinstance(
                    pipeline_data["execution"]["max_threads"], int
                ):
                    max_threads = pipeline_data["execution"]["max_threads"]
                    self._logger.debug(
                        f"Processing execution max_threads: {max_threads}"
                    )

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

    def _normalize_pipeline_modules(self, pipeline_data: Dict) -> None:
        """
        Process pipeline modules to normalize their structure for the Pipeline dataclass.

        This method handles the conversion of the new format fields like id, module, input, outputs
        to the format needed by the Pipeline dataclass.

        :param pipeline_data: The parsed pipeline data to normalize
        """
        if "modules" not in pipeline_data or not isinstance(
            pipeline_data["modules"], list
        ):
            return

        for module in pipeline_data["modules"]:
            if not isinstance(module, dict):
                continue

            # Ensure module has a name field (copy from module field if needed)
            if "module" in module:
                module["name"] = module["module"]

            # Log module ID mapping
            if "id" in module:
                self._logger.debug(
                    f"Module with ID '{module['id']}' mapped to name '{module['name']}'"
                )

            # Handle 'input' field and convert to input_mappings with qualified names
            if "input" in module and isinstance(module["input"], dict):
                # Create input_mappings if not present
                if "input_mappings" not in module:
                    module["input_mappings"] = {}

                # Process inputs format: input_name: module_id.output_name
                for input_name, input_source in module["input"].items():
                    if "." in input_source:
                        # This is the new qualified format with module_id.output_name
                        # Split into module_id and output_name parts
                        source_parts = input_source.split(".", 1)
                        module_id = source_parts[0]
                        output_name = source_parts[1]

                        # Store in input_mappings for proper connection later
                        module["input_mappings"][input_name] = output_name

                        # Store the source module ID for dependency resolution
                        if "depends_on" not in module:
                            module["depends_on"] = []

                        # Add the module_id to depends_on if not already there
                        if module_id not in module["depends_on"]:
                            module["depends_on"].append(module_id)

                        self._logger.debug(
                            f"Mapped input '{input_name}' to '{input_source}' "
                            + f"(added dependency on '{module_id}')"
                        )
                    else:
                        # Simple name format, just copy to input_mappings
                        module["input_mappings"][input_name] = input_source

                # Remove the original 'input' field since we've processed it
                del module["input"]

            # Normalize outputs format
            if "outputs" in module and isinstance(module["outputs"], list):
                processed_outputs = []
                for output_item in module["outputs"]:
                    if isinstance(output_item, str):
                        # Simple string output
                        processed_outputs.append({"name": output_item})
                    elif isinstance(output_item, dict):
                        # Dict format {key: value} for output mapping
                        for output_name, mapped_name in output_item.items():
                            processed_outputs.append(
                                {"name": output_name, "mapped": mapped_name}
                            )
                    else:
                        # Already in correct format or unrecognized
                        processed_outputs.append(output_item)

                module["outputs"] = processed_outputs
