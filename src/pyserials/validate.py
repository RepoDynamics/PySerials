import jsonschema as _jsonschema
from referencing.exceptions import Unresolvable as _UnresolvableReferencingError
import pyserials.exception as _exception


def jsonschema(
    data: dict | list | str | int | float | bool,
    schema: dict,
    validator: _jsonschema.validators.Validator = _jsonschema.Draft202012Validator,
    fill_defaults: bool = True,
) -> None:
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
    common_error_args = {"data": data, "schema": schema, "validator": validator}
    try:
        validator(schema).validate(data)
    except (_jsonschema.exceptions.ValidationError, _jsonschema.exceptions.FormatError) as e:
        raise _exception.ValidationError(
            error_type=_exception.ValidationErrorType.DATA_INVALID,
            **common_error_args,
        ) from e
    except (
        _jsonschema.exceptions.SchemaError,
        _jsonschema.exceptions.UndefinedTypeCheck,
        _jsonschema.exceptions.UnknownType,
        _UnresolvableReferencingError,
    ) as e:
        raise _exception.ValidationError(
            error_type=_exception.ValidationErrorType.SCHEMA_INVALID,
            **common_error_args,
        ) from e
    return
