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
    types.Struct.type_id:   {"type": "object"}
    types.Map.type_id:      {},
    types.Set.type_id:      {"type": "array"},
    types.List.type_id:     {"type": "array"},
    types.Tuple.type_id:    {"type": "array"},
    types.JSONData.type_id: None
}



class JSONFieldData(object):

    def __init__(
            self,
            property_name=None,
            # is_unboxed only makes sense for Struct type fields
            is_unboxed=False):
        self.property_name = property_name
        self.is_unboxed = is_unboxed


class JSONTypeData(object):

    def __init__(
            self,
            type_name=None):
        self.type_name = type_name


def get_field_name(field):
    if field.metadata and\
            'json' in field.metadata.backend_data and\
            field.metadata.backend_data['json'].property_name:
        return field.metadata.backend_data['json'].property_name
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
    json_backend_data = field.metadata.backend_data.get('json', None)
    if not json_backend_data:
        return False
    if not isinstance(json_backend_data, JSONFieldData):
        return False
    return json_backend_data.is_unboxed
