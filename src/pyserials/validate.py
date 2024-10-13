import jsonschema as _jsonschema
import referencing as _referencing
import referencing.jsonschema as _referencing_jsonschema
from referencing.exceptions import Unresolvable as _UnresolvableReferencingError
import pyserials.exception as _exception


def jsonschema(
    data: dict | list | str | int | float | bool,
    schema: dict,
    validator: type[_jsonschema.protocols.Validator] = _jsonschema.Draft202012Validator,
    registry: _referencing_jsonschema.SchemaRegistry | None = None,
    fill_defaults: bool = True,
    iter_errors: bool = False,
    raise_invalid_data: bool = True,
) -> list[_jsonschema.exceptions.ValidationError]:
    """
    Validate data against a JSON schema.

    Parameters
    ----------
    data : dict | list | str | int | float | bool
        The data to validate.
    schema : dict
        The schema to validate the data against.
    validator : jsonschema.protocols.Validator, default: jsonschema.Draft202012Validator
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
    def _extend_with_default(validator_class: _jsonschema.protocols.Validator) -> _jsonschema.protocols.Validator:
        # https://python-jsonschema.readthedocs.io/en/stable/faq/#why-doesn-t-my-schema-s-default-property-set-the-default-on-my-instance

        validate_properties = validator_class.VALIDATORS["properties"]

        def set_defaults(validator, properties, instance, schema):
            if isinstance(instance, dict):  # The entire dict instance may be templated
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

    error_args = {"data": data, "schema": schema, "validator": validator, "registry": registry}
    validator = _extend_with_default(validator) if fill_defaults else validator
    try:
        validator_instance = validator(schema, registry=registry) if registry else validator(schema)
    except (
        _jsonschema.exceptions.SchemaError,
        _jsonschema.exceptions.UndefinedTypeCheck,
        _jsonschema.exceptions.UnknownType,
        _UnresolvableReferencingError,
    ) as e:
        raise _exception.validate.PySerialsInvalidJsonSchemaError(**error_args) from e
    if iter_errors:
        errors = list(validator_instance.iter_errors(data))
    else:
        try:
            validator_instance.validate(data)
            errors = []
        except (_jsonschema.exceptions.ValidationError, _jsonschema.exceptions.FormatError) as e:
            errors = [e]
    if raise_invalid_data and errors:
        error_args["validator"] = validator_instance
        raise _exception.validate.PySerialsJsonSchemaValidationError(**error_args, causes=errors)
    return errors
