""" Schema for unimodel objects.
    This allow us to do several things:
    - Encode the schema of the message along with the message itself
    - Build ASTs for generators which take eg. jsonschema as input
    - Create classes at runtime based on a schema (jsonschema or thrift)
    etc.
"""

from unimodel.model import Unimodel, UnimodelUnion, Field, FieldFactory
from unimodel.types import *
from unimodel.backends.json.type_data import JSONFieldData

class SchemaObjectMetadata(Unimodel):
    annotations = Field(Map(UTF8, UTF8))
    # TODO: validators
    backend_data = Field(
                    Map(
                        UTF8,  # Key is the name of the backend, eg: 'thrift'
                        # data for each backend should be represented as a simple dict
                        Map(UTF8, UTF8)))

class SchemaObject(Unimodel):
    name = Field(UTF8, required=True)
    metadata = Field(Struct(SchemaObjectMetadata))

schema_object_field = Field(
    Struct(SchemaObject),
    required=True,
    metadata=Metadata(
        backend_data={'json': JSONFieldData(is_unboxed=True)}))

type_id_enum = Enum({
    1: "utf8",
    2: "int64",
    3: "int32",
    4: "int16",
    5: "int8",
    6: "double",
    7: "bool",
    8: "struct",
    9: "union",
    10: "enum",
    11: "list",
    12: "set",
    13: "map",
    14: "binary"})

# TypeDef is recursive because of ParametricType
class TypeDef(Unimodel):

    def __init__(self, type_constructor=None, **kwargs):
        super(TypeDef, self).__init__(**kwargs)
        self.type_constructor = type_constructor

class ParametricType(Unimodel):
    type_id = Field(type_id_enum, required=True)
    type_parameters = Field(List(TypeDef), required=True)

class TypeClass(UnimodelUnion):
    primitive_type_id = Field(type_id_enum)
    enum = Field(Map(Int, UTF8))
    struct_name = Field(UTF8)
    parametric_type = Field(Struct(ParametricType))

field_factory = FieldFactory()
field_factory.add_fields(TypeDef, {
    'common': schema_object_field,
    'type_class': Field(Union(TypeClass), required=True)})

class Literal(UnimodelUnion):
    integer = Field(Int)
    double = Field(Double)
    string = Field(UTF8)

class FieldDef(Unimodel):
    common = schema_object_field
    field_type = Field(Struct(TypeDef), required=True)
    required = Field(Bool, default=False)
    default = Field(Union(Literal))

class StructDef(Unimodel):
    common = schema_object_field
    fields = Field(List(Struct(FieldDef)), required=True)

class ModelSchema(Unimodel):
    common = schema_object_field
    description = Field(UTF8)
    structs = Field(List(Struct(StructDef)))
    root_struct_name = Field(UTF8)
