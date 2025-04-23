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
        # Revert to original: Get path from FileSystem, which now checks env vars
        self._pipeline_dir = FileSystem.get_pipelines_directory()
        self._logger.info(f"Pipeline directory set to: {self._pipeline_dir}")

    def load_pipeline(self, pipeline_name: str) -> Optional[Pipeline]:
        """
        Load a pipeline configuration from the specified YAML file.

        Args:
            pipeline_name: Name of the pipeline (without .yaml extension)

        Returns:
            Pipeline object or None if loading fails
        """
        pipeline_path = os.path.join(self._pipeline_dir, f"{pipeline_name}.yaml")
        self._logger.debug(f"Loading pipeline from: {pipeline_path}")

        try:
            # Check if file exists
            if not os.path.exists(pipeline_path):
                self._logger.error(f"Pipeline file not found: {pipeline_path}")
                return None

            # Load YAML file
            with open(pipeline_path, "r", encoding="utf-8") as file:
                pipeline_data = yaml.safe_load(file)

            # Check if pipeline data is nested under a 'pipeline' key and extract it if needed
            if isinstance(pipeline_data, dict) and "pipeline" in pipeline_data:
                self._logger.debug(
                    "Pipeline data is nested under 'pipeline' key, extracting..."
                )
                pipeline_data = pipeline_data["pipeline"]

            # Normalize pipeline modules structure if needed
            self._normalize_pipeline_modules(pipeline_data)

            # Convert to Pipeline object using dacite
            try:
                pipeline = from_dict(
                    data_class=Pipeline,
                    data=pipeline_data,
                    config=self._get_dacite_config(),
                )
                self._logger.debug(
                    f"Successfully loaded pipeline '{pipeline.name}' with {len(pipeline.modules)} modules"
                )
                return pipeline
            except ForwardReferenceError as e:
                self._logger.error(
                    f"Forward reference error in pipeline '{pipeline_name}': {e}"
                )
            except UnexpectedDataError as e:
                self._logger.error(
                    f"Unexpected data in pipeline '{pipeline_name}': {e}"
                )
            except WrongTypeError as e:
                self._logger.error(f"Wrong type in pipeline '{pipeline_name}': {e}")
            except MissingValueError as e:
                self._logger.error(
                    f"Missing required value in pipeline '{pipeline_name}': {e}"
                )
            except Exception as e:
                self._logger.error(f"Failed to parse pipeline '{pipeline_name}': {e}")

        except yaml.YAMLError as e:
            self._logger.error(f"Invalid YAML in pipeline '{pipeline_name}': {e}")
        except Exception as e:
            self._logger.error(f"Error loading pipeline '{pipeline_name}': {e}")

        return None

    def list_pipelines(self) -> List[Dict]:
        """
        List all available pipelines with basic information.

        Returns:
            List of dictionaries with pipeline info
        """
        result = []
        pipelines_dir = self._pipeline_dir
        self._logger.debug(f"Listing pipelines from directory: {pipelines_dir}")

        try:
            # Get all YAML files in the pipeline directory
            yaml_files = [
                f
                for f in os.listdir(pipelines_dir)
                if os.path.isfile(os.path.join(pipelines_dir, f))
                and f.endswith(".yaml")
            ]

            # Load basic information from each pipeline file
            for yaml_file in yaml_files:
                pipeline_path = os.path.join(pipelines_dir, yaml_file)
                pipeline_name = os.path.splitext(yaml_file)[0]

                try:
                    with open(pipeline_path, "r", encoding="utf-8") as file:
                        pipeline_data = yaml.safe_load(file)

                    # Extract basic information
                    info = {
                        "name": pipeline_name,
                        "display_name": pipeline_data.get("name", pipeline_name),
                        "description": pipeline_data.get("description", ""),
                        "modules_count": len(pipeline_data.get("modules", [])),
                        "filename": yaml_file,
                    }
                    result.append(info)
                except Exception as e:
                    self._logger.warning(
                        f"Error reading pipeline '{pipeline_name}': {e}"
                    )
                    # Include with minimal information
                    result.append(
                        {
                            "name": pipeline_name,
                            "display_name": pipeline_name,
                            "description": "Error loading pipeline",
                            "modules_count": 0,
                            "filename": yaml_file,
                            "error": str(e),
                        }
                    )
        except Exception as e:
            self._logger.error(f"Error listing pipelines: {e}")

        return result

    def _get_dacite_config(self):
        """
        Create configuration for dacite to handle optional fields.

        Returns:
            Dacite configuration object
        """
        # Import Config class from dacite
        from dacite.config import Config
        from typing import Dict, List, Any, Union

        # This configuration tells dacite how to handle optional fields
        # Using the Config class instead of a dict to ensure all required attributes are present
        return Config(
            check_types=True,
            strict=True,  # Enforce strict type checking
            cast=[str, int, float, bool],  # Basic type casting
            type_hooks={
                List: lambda x: [] if x is None else x,
                Dict: lambda x: {} if x is None else x,
            },
        )

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

            if "config" in module and isinstance(module["config"], dict):
                for key, value in module["config"].items():
                    module["config"][key] = value

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
