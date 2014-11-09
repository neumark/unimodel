""" Schema for unimodel objects.
    This allow us to do several things:
    - Encode the schema of the message along with the message itself
    - Build ASTs from generators which take eg. jsonschema as input
    - Create classes at runtime based on a schema (jsonschema or thrift)
    etc.
"""

from unimodel.model import Unimodel, UnimodelUnion, Field, FieldFactory
from unimodel import types
from unimodel.backends.json.type_data import JSONFieldData
from unimodel.metadata import Metadata
import inspect

def get_type_id_to_name_dict():
    type_dict = {}
    for type_name in dir(types):
        t = getattr(types, type_name)
        if inspect.isclass(t) and issubclass(t, types.FieldType) and hasattr(t, 'type_id'):
            type_dict[t.type_id] = t.__name__.lower()
    return type_dict


class SchemaObjectMetadata(Unimodel):
    annotations = Field(types.Map(types.UTF8, types.UTF8))
    # TODO: validators
    backend_data = Field(
                    types.Map(
                        types.UTF8,  # Key is the name of the backend, eg: 'thrift'
                        # data for each backend should be represented as a simple dict
                        types.Map(types.UTF8, types.UTF8)))

class SchemaObject(Unimodel):
    name = Field(types.UTF8, required=True)
    metadata = Field(types.Struct(SchemaObjectMetadata))

schema_object_field = Field(
    types.Struct(SchemaObject),
    required=True,
    metadata=Metadata(
        backend_data={'json': JSONFieldData(is_unboxed=True)}))

type_id_enum = types.Enum(get_type_id_to_name_dict())

# TypeDef is recursive because of ParametricType
class TypeDef(Unimodel):

    def __init__(self, type_constructor=None, **kwargs):
        super(TypeDef, self).__init__(**kwargs)
        self.type_constructor = type_constructor

class ParametricType(Unimodel):
    type_id = Field(type_id_enum, required=True)
    type_parameters = Field(types.List(types.Struct(TypeDef)), required=True)

class TypeClass(UnimodelUnion):
    primitive_type_id = Field(type_id_enum)
    enum = Field(types.Map(types.Int, types.UTF8))
    struct_name = Field(types.UTF8)
    parametric_type = Field(types.Struct(ParametricType))

field_factory = FieldFactory()
field_factory.add_fields(TypeDef, {
    'metadata': Field(types.Struct(SchemaObjectMetadata)),
    'type_class': Field(types.Struct(TypeClass), required=True)})

class Literal(UnimodelUnion):
    integer = Field(types.Int)
    double = Field(types.Double)
    string = Field(types.UTF8)

class FieldDef(Unimodel):
    common = schema_object_field
    field_type = Field(types.Struct(TypeDef), required=True)
    required = Field(types.Bool, default=False)
    default = Field(types.Struct(Literal))

class StructDef(Unimodel):
    common = schema_object_field
    is_union = Field(types.Bool, default=False)
    fields = Field(types.List(types.Struct(FieldDef)), required=True)

class TupleDef(Unimodel):
    common = schema_object_field
    types = Field(types.List(types.Struct(TypeDef)), required=True)

class ModelSchema(Unimodel):
    common = schema_object_field
    description = Field(types.UTF8)
    structs = Field(types.List(types.Struct(StructDef)))
    root_struct_name = Field(types.UTF8)
