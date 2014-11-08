import json
import jsonschema
from unimodel.schema import *
from unimodel import types

class TypeReference(object):
    REF_ATTR = '$ref'
    @classmethod
    def is_ref(cls, definition):
        return TypeReference.REF_ATTR in definition
    def __init__(self, definition):
        self.ref = definition[TypeReference.REF_ATTR]

class JSONSchemaModelGenerator(object):
    # From: http://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types 
    # Name     type    format    Comments
    # --       --      --        --
    # integer  integer int32     signed 32 bits
    # long     integer int64     signed 64 bits
    # float    number  float   
    # double   number  double  
    # string   string          
    # byte     string  byte    
    # boolean  boolean         
    # date     string  date      As defined by full-date - RFC3339
    # dateTime string  date-time As defined by date-time - RFC3339

    # Maps (type, format) -> (unimodel type name, type constructor class)
    # based on the table above. Unimodel names take from unimodel.schema.type_id_enum
    JSON_TO_UNIMODEL_TYPE = {
        ('integer', None)       : ('int64', types.Int64),
        ('integer', 'int32')    : ('int32', types.Int32),
        ('integer', 'int64')    : ('int64', types.Int64),
        ('number', None)        : ('double', types.Double),
        ('number', 'float')     : ('double', types.Double),
        ('number', 'double')    : ('double', types.Double),
        ('string', None)        : ('utf8', types.UTF8),
        ('string', 'byte')      : ('utf8', types.UTF8), # TODO: make this a byte UTF8 subclass
        ('string', 'date')      : ('utf8', types.UTF8), # TODO: make this a date UTF8 subclass
        ('string', 'date-time') : ('utf8', types.UTF8), # TODO: make this a date-time UTF8 subclass
        ('string', 'uri')       : ('utf8', types.UTF8), # TODO: make this a URI UTF8 subclass
        ('string', 'email')     : ('utf8', types.UTF8), # TODO: make this an email UTF8 subclass
        ('boolean', None)       : ('bool', types.Bool),
        ('array', None)         : ('list', types.List),
        # 'object' can mean map or struct, but structs are
        # listed directly under 'definitions', everywhere else,
        # they are $ref'd.
        ('object', None)         : ('map', types.Map),
        # Enums have the 'string' type in jsonschema. An additional
        # 'enum' property identifies them as such.
    }


    def __init__(self, name, schema):
        self.name = name
        self.schema = schema
        self.type_definitions = {}
        self.unparsed = {}

    def resolve_type_refs(self, model_obj):
        """ replaces TypeReference objects with the type definitions they refer to """
        if isinstance(model_obj, Unimodel):
            for name, value in model_obj.items():
                if isinstance(value, TypeReference):
                    model_obj.field_type = field_type=TypeDef(
                        common=SchemaObject(name="struct"),
                        # TODO: repalce value.ref with struct name!
                        type_class=TypeClass(struct_name=value.ref))
                    continue
                if isinstance(value, Unimodel):
                    self.resolve_type_refs(value)
                if isinstance(value, dict):
                    for v in value.values():
                        self.resolve_type_refs(v)
                if isinstance(value, list):
                    for v in value:
                        self.resolve_type_refs(v)
        return model_obj

    def generate_type(self, definition):
        # TODO: fix anyOf, allOf and not!
        if not 'type' in definition:
            self.unparsed[len(self.unparsed)] = definition
            return None
        json_type = definition['type']
        json_format = definition.get('format', None)
        enum = definition.get('enum', None)

        if enum:
            type_name = "enum"
        else:
            type_name, type_cons = self.JSON_TO_UNIMODEL_TYPE[(json_type, json_format)]
        type_def = TypeDef(
                common = SchemaObject(name = type_name))
        # type type is never "struct" or "union", because
        # that will be replaced by a typereference
        if enum:
            type_def.type_class = TypeClass(
                enum=dict(zip(
                    xrange(0, len(enum)),
                    enum)))
        elif issubclass(type_cons, types.List):
            # TODO
            type_def.type_class = TypeClass(parametric_type=ParametricType())
        elif issubclass(type_cons, types.Map):
            # TODO
            type_def.type_class = TypeClass(parametric_type=ParametricType())
        else:  # primitive type
            type_def.type_class = TypeClass(primitive_type_id=type_id_enum.name_to_key(type_name))
        return type_def

    def generate_field(self, name, definition, required=False):
        field_def = FieldDef(
            common = SchemaObject(name=name),
            required = required)
        if TypeReference.is_ref(definition):
            field_def.field_type = TypeReference(definition)
        else:
            field_def.field_type = self.generate_type(definition)
        return field_def

    def generate_struct(self, name, definition):
        field_list = []
        required_fields = definition.get('required', [])
        struct_def = StructDef(
            common = SchemaObject(name=name),
            fields = field_list)
        for field_name, field_definition in definition.get('properties', {}).items():
            field_list.append(self.generate_field(
                field_name,
                field_definition,
                field_name in required_fields))
        return struct_def

    def generate_model_schema(self):
        # generate models for structs in definitions
        struct_list = []
        model_schema = ModelSchema(
            common = SchemaObject(name = self.name),
            description = self.schema.get('description', ''),
            structs = struct_list)
        for name, definition in self.schema.get('definitions', {}).items():
            if TypeReference.is_ref(definition):
                self.type_definitions[name] = TypeReference(definition)
                continue
            if not 'type' in definition:
                # skip definitions without a 'type' field for now
                self.unparsed[name] = definition
                continue
            if definition['type'] == 'object':
                struct = self.generate_struct(name, definition)
                struct_list.append(struct)
            else:
                self.type_definitions[name] = self.generate_type(definition)
        self.resolve_type_refs(model_schema)
        return model_schema
