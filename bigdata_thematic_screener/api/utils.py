from typing import Type

from pydantic import BaseModel

from bigdata_thematic_screener.api.examples import EXAMPLE_REPORT, EXAMPLE_STATUS
from bigdata_thematic_screener.api.sql_models import (
    SQLThematicScreenerReport,
    SQLWorkflowStatus,
)


def get_example_values_from_schema(schema_model: Type[BaseModel]) -> dict:
    """
    Extract example values from a Pydantic model's fields, falling back to defaults if no example is provided.
    Args:
        schema_model: The Pydantic model class (not instance).
    Returns:
        dict: Mapping of field names to example or default values.
    """
    example_values = {}
    for field_name, field in schema_model.model_fields.items():
        if isinstance(field.json_schema_extra, dict):
            if "example" in field.json_schema_extra:
                example = field.json_schema_extra["example"]
        else:
            example = None
        if example is not None:
            example_values[field_name] = example
        else:
            example_values[field_name] = field.default
    return example_values


def status_report_example_models() -> tuple[
    SQLWorkflowStatus, SQLThematicScreenerReport
]:
    """
    Returns a tuple with example instances of SQLWorkflowStatus and SQLThematicScreenerReport models.
    To use for initialization of the database with example data.
    """

    return EXAMPLE_STATUS, EXAMPLE_REPORT
