import jsonschema as _jsonschema
from referencing.exceptions import Unresolvable as _UnresolvableReferencingError
import pyserials.exception as _exception


def jsonschema(
    data: dict | list | str | int | float | bool,
    schema: dict,
    validator: _jsonschema.validators.Validator = _jsonschema.Draft202012Validator,
    fill_defaults: bool = True,
    raise_invalid_data: bool = True,
) -> bool:
    """
    Validate data against a JSON schema.

    Parameters
    ----------
    data : dict | list | str | int | float | bool
        The data to validate.
    schema : dict
        The schema to validate the data against.
    validator : jsonschema.validators.Validator, default: jsonschema.Draft202012Validator
        The JSON schema validator to use.
    fill_defaults : bool, default: True
        Whether to fill in the data with default values from the schema,
        when they are not present.
    raise_invalid_data : bool, default: True
        Whether to raise an exception when the data is invalid against the schema.

    Returns
    -------
    valid : bool
        Whether the data is valid against the schema.

    Raises
    ------
    pyserials.exception.PySerialsInvalidSchemaError
        If the schema is invalid.
    pyserials.exception.PySerialsSchemaValidationError
        If the data is invalid against the schema and `raise_invalid_data` is `True`.
    """
    def _extend_with_default(validator_class):
        # https://python-jsonschema.readthedocs.io/en/stable/faq/#why-doesn-t-my-schema-s-default-property-set-the-default-on-my-instance

        validate_properties = validator_class.VALIDATORS["properties"]

        def set_defaults(validator, properties, instance, schema):
            for property, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(property, subschema["default"])

            for error in validate_properties(
                validator,
                properties,
                instance,
                schema,
            ):
                yield error

        return _jsonschema.validators.extend(validator_class, {"properties": set_defaults})

    validator = _extend_with_default(validator) if fill_defaults else validator
    error_args = {"data": data, "schema": schema, "validator": validator}
    try:
        validator(schema).validate(data)
    except (
        _jsonschema.exceptions.SchemaError,
        _jsonschema.exceptions.UndefinedTypeCheck,
        _jsonschema.exceptions.UnknownType,
        _UnresolvableReferencingError,
    ) as e:
        raise _exception.validate.PySerialsInvalidSchemaError(**error_args) from e
    except (_jsonschema.exceptions.ValidationError, _jsonschema.exceptions.FormatError) as e:
        if raise_invalid_data:
            raise _exception.validate.PySerialsSchemaValidationError(**error_args) from e
        return False
    return True
