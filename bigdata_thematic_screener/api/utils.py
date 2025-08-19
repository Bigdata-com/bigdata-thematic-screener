from typing import Type

from pydantic import BaseModel


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
        example = None
        if hasattr(field, "json_schema_extra") and field.json_schema_extra:
            example = field.json_schema_extra.get("example")
        if example is not None:
            example_values[field_name] = example
        else:
            example_values[field_name] = field.default
    return example_values
