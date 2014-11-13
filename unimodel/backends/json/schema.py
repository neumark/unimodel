from unimodel.backends.base import SchemaWriter
import copy
import json
from unimodel import types
from unimodel.backends.json.type_data import get_field_name

"""
Useful: http://www.jsonschema.net/
Example: from http://json-schema.org/example2.html
"""


"""
A map looks something like this:
(taken from:
https://github.com/swagger-api/swagger-spec/blob/master/fixtures/v2.0/json/models/modelWithInt32Map.json)
{
  "description": "This is a Map[String, Integer]",
  "additionalProperties": {
    "type": "integer",
    "format": "int32"
  }
}"""

MAP_DEFINITION_TEMPLATE = {
    "description": "map",
    "additionalProperties": True,
    "required": [],  # Fill with required field names
}

STRUCT_MAP_DEFINITION_TEMPLATE = {
    "type": "object",
    "properties": {},  # Fill with field definitions
    "additionalProperties": True,
    "required": [],  # Fill with required field names
}

SCHEMA_TEMPLATE = dict(copy.deepcopy(
    STRUCT_MAP_DEFINITION_TEMPLATE).items() + {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": None,  # Replace with schema description
    "definitions": {}  # Fill struct and map type definitions
}.items())

BASIC_FIELD_TEMPLATE = {
    "type": None  # Replace with basic type name, eg: "string"
}

LIST_TEMPLATE = {
    "type": "array",
    "items": {
        "type": None  # Replace with type reference to definition of elements
    },
    "uniqueItems": False  # set to True for sets
}


class JSONSchemaWriter(SchemaWriter):

    def __init__(self, *args, **kwargs):
        super(JSONSchemaWriter, self).__init__(*args, **kwargs)

    def get_schema_ast(self, root_struct_class):
        # Collect struct dependencies of root struct (if any).
        struct_dependencies = self.get_dependencies_for_one_struct(
            root_struct_class)
        # Collect struct dependencies of manually added struct classes (if
        # any).
        for struct_class in self.struct_classes:
            self.get_dependencies_for_one_struct(
                struct_class,
                struct_dependencies)
        schema = copy.deepcopy(SCHEMA_TEMPLATE)
        schema['description'] = self.description
        # Note, the root class will be added to the definitions list
        # even if it is only used to desribe the top-level object.
        schema['definitions'] = dict(
            [self.get_struct_definition(s) for s in struct_dependencies])
        self.add_struct_properties(root_struct_class, schema)
        return schema

    def get_struct_definition(self, struct_class):
        """ returns (name, definition) pairs """
        struct_def = copy.deepcopy(STRUCT_MAP_DEFINITION_TEMPLATE)
        self.add_struct_properties(struct_class, struct_def)
        return (struct_class.get_name(), struct_def)

    def add_struct_properties(self, struct_class, struct_def):
        if struct_class.get_field_definitions():
            required = []
            for field in struct_class.get_field_definitions():
                field_name = get_field_name(field)
                struct_def['properties'][
                    field_name] = self.get_type_definition(field.field_type)
                if field.required:
                    required.append(field_name)
            struct_def['required'] = required
        if 'required' in struct_def and not struct_def['required']:
            del struct_def['required']

    def get_type_definition(self, type_definition):
        """ returns field (name, definition) pair """
        if isinstance(type_definition, types.Enum):
            return self.define_enum_field(type_definition)
        if isinstance(type_definition, types.NumberType):
            return self.define_basic_field(type_definition)
        if isinstance(type_definition, types.UTF8):
            return self.define_basic_field(type_definition)
        if isinstance(type_definition, types.Bool):
            return self.define_basic_field(type_definition)
        if isinstance(type_definition, types.Struct):
            # Since all the structs were already collected, and are
            # defined in the definitions section, it's enough to refer
            # to the struct here.
            return self.reference_type(type_definition)
        if isinstance(type_definition, types.Map):
            return self.define_map_field(type_definition)
        if isinstance(type_definition, types.List):
            return self.define_list(type_definition)
        raise Exception(
            "Cannot create schema for type %s" %
            str(type_definition))

    def define_basic_field(self, type_definition):
        field_def = copy.deepcopy(BASIC_FIELD_TEMPLATE)
        field_def['type'] = type_definition.metadata.backend_data[
            'json'].type_name
        return field_def

    def define_enum_field(self, type_definition):
        field_def = {'enum': type_definition.names()}
        return field_def

    def reference_type(self, type_definition):
        return {
            "$ref": "#/definitions/%s" %
            type_definition.python_type.get_name()}

    def define_map_field(self, type_definition):
        # It's not possible to write a schema for a map type on jsonschema.
        # Yes, I know it's crazy. I'm not the one who wanted to ditch Thrift
        # for this crap! :)
        field_def = copy.deepcopy(STRUCT_MAP_DEFINITION_TEMPLATE)
        del field_def['required']
        return field_def

    def define_list(self, type_definition):
        field_def = copy.deepcopy(LIST_TEMPLATE)
        field_def['items'] = self.get_type_definition(
            type_definition.type_parameters[0])
        if isinstance(type_definition, types.Set):
            field_def['uniqueItems'] = True
        return field_def

    def get_dependencies_for_field_type(self, field_type, struct_dependencies):
        if isinstance(field_type, types.Struct):
            self.get_dependencies_for_one_struct(
                field_type.python_type,
                struct_dependencies)
        if field_type.type_parameters:
            for type_parameter in field_type.type_parameters:
                self.get_dependencies_for_field_type(
                    type_parameter,
                    struct_dependencies)

    def get_dependencies_for_one_struct(self, cls, struct_dependencies=None):
        # It's possible that struct_class is actually an implementation class
        # In this case, we want the interface class
        struct_dependencies = struct_dependencies or set()
        struct_class = self.model_registry.lookup_interface(cls)
        if struct_class in struct_dependencies:
            # For recursive types, quit if type has already been encountered
            return struct_dependencies
        # recursively traverse the fields of the struct, looking for new
        # dependencies
        struct_dependencies.add(struct_class)
        if struct_class.get_field_definitions():
            for field in struct_class.get_field_definitions():
                self.get_dependencies_for_field_type(
                    field.field_type,
                    struct_dependencies)
        return struct_dependencies

    def get_schema_text(self, *args, **kwargs):
        return json.dumps(
            self.get_schema_ast(*args, **kwargs),
            sort_keys=True,
            indent=4,
            separators=(',', ': '))
