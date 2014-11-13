from unimodel import types
from thrift.Thrift import TType

type_id_mapping = {
    types.Bool.type_id: TType.BOOL,
    types.Int8.type_id: TType.BYTE,
    types.Int16.type_id: TType.I16,
    types.Int32.type_id: TType.I32,
    types.Int64.type_id: TType.I64,
    types.BigInt.type_id: TType.STRING,
    types.Enum.type_id: TType.I64,
    types.UTF8.type_id: TType.STRING,
    types.Binary.type_id: TType.STRING,
    types.Double.type_id: TType.DOUBLE,
    types.Struct.type_id: TType.STRUCT,
    types.Map.type_id: TType.MAP,
    types.Set.type_id: TType.SET,
    types.List.type_id: TType.LIST,
    types.Tuple.type_id: TType.STRUCT,
    types.JSONData.type_id: TType.STRING,
}

def type_name(field):
    from unimodel import types
    thrift_type_id = type_id_mapping[field.field_type.type_id]
    name = TType._VALUES_TO_NAMES[thrift_type_id].lower()
    if name == "string" and thrift_type_data.is_binary:
        name = "binary"
    if name == "struct" and isinstance(
            field.field_type.get_python_type(),
            UnimodelUnion):
        name = "union"
    # Note: no need to check for tuple, because they are structs too
    # according to Thrift
    if thrift_type_data.field_type.type_parameters:
        name += "<%s>" % ", ".join([
            t.type_name()
            for t in thrift_type_data.field_type.type_parameters])
    return name
