from unimodel import types

# From:
# github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#data-types
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


type_id_mapping = {
    types.Bool.type_id:     {"type": "boolean"},
    types.Int8.type_id:     {"type": "integer", "format": "int32"},
    types.Int16.type_id:    {"type": "integer", "format": "int32"},
    types.Int32.type_id:    {"type": "integer", "format": "int32"},
    types.Int64.type_id:    {"type": "integer", "format": "int64"},
    types.BigInt.type_id:   {"type": "integer"},
    types.Enum.type_id:     {"type": "string"},
    types.UTF8.type_id:     {"type": "string"},
    types.Binary.type_id:   {"type": "string", "format": "byte"},
    types.Double.type_id:   {"type": "number", "format": "double"},
    types.Struct.type_id:   {"type": "object"},
    types.Map.type_id:      None,
    types.Set.type_id:      {"type": "array"},
    types.List.type_id:     {"type": "array"},
    types.Tuple.type_id:    {"type": "array"},
    types.JSONData.type_id: None
}

# the following constants refer to metadata dictionary keys
# for json-backend-specific information.
# -- Fields --
MDK_FIELD_NAME = "field.name"
# -- Types --
MDK_TYPE_STRUCT_UNBOXED = "type.struct.unboxed"

def get_field_name(field):
    if field.metadata:
        field_name = field.metadata.get_backend_data("json", MDK_FIELD_NAME)
        if field_name:
            return field_name
    return field.field_name


def get_field_by_name(struct_class, name):
    for field in struct_class.get_field_definitions():
        if get_field_name(field) == name:
            return field
    return None

def is_unboxed_struct_field(field):
    from unimodel.types import Struct
    if not isinstance(field.field_type, Struct):
        return False
    if not field.metadata:
        return False
    return field.metadata.get_backend_data("json", MDK_TYPE_STRUCT_UNBOXED)
