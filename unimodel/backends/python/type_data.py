from unimodel import types

try:
    STR_TYPE = basestring  # attempt to evaluate basestring
    BIN_TYPE = str
except NameError:
    STR_TYPE = str
    BIN_TYPE = bytes


type_id_mapping = {
    types.Bool.type_id:     bool,
    types.Int8.type_id:     int,
    types.Int16.type_id:    int,
    types.Int32.type_id:    int,
    types.Int64.type_id:    int,
    types.BigInt.type_id:   long,
    types.Enum.type_id:     int,
    types.UTF8.type_id:     STR_TYPE,
    types.Binary.type_id:   BIN_TYPE,
    types.Double.type_id:   float,
    types.Struct.type_id:   None,  # this will be the class of the struct
    types.Map.type_id:      dict,
    types.Set.type_id:      set,
    types.List.type_id:     list,
    types.Tuple.type_id:    tuple,
    types.JSONData.type_id: None
}


