# This file is for classes holding Thrift-specific data for types and fields.
# Since this is imported form unimodel/types.py, it's important not to
# import the whole apache thrift python lib from this file.
# Instead the TType class is duplicated here.


class TType:
    STOP = 0
    VOID = 1
    BOOL = 2
    BYTE = 3
    I08 = 3
    DOUBLE = 4
    I16 = 6
    I32 = 8
    I64 = 10
    STRING = 11
    UTF7 = 11
    STRUCT = 12
    MAP = 13
    SET = 14
    LIST = 15
    UTF8 = 16
    UTF16 = 17

    _VALUES_TO_NAMES = ('STOP',
                        'VOID',
                        'BOOL',
                        'BYTE',
                        'DOUBLE',
                        None,
                        'I16',
                        None,
                        'I32',
                        None,
                        'I64',
                        'STRING',
                        'STRUCT',
                        'MAP',
                        'SET',
                        'LIST',
                        'UTF8',
                        'UTF16')


class ThriftTypeData(object):

    def __init__(
            self,
            type_id=-1,  # Note: The default value is invalid
            is_binary=False,
            is_union=False,
            is_tuple=False):
        self.type_id = type_id
        self.is_binary = is_binary
        self.is_union = is_union
        self.is_tuple = is_tuple

    @classmethod
    def type_name(cls, field):
        from unimodel.model import UnimodelUnion
        thrift_type_data = field.field_type.metadata.backend_data['thrift']
        name = TType._VALUES_TO_NAMES[thrift_type_data.type_id].lower()
        if name == "string" and thrift_type_data.is_binary:
            name = "binary"
        if name == "struct" and isinstance(
                field.field_type.python_type,
                UnimodelUnion):
            name = "union"
        # Note: no need to check for tuple, because they are structs too
        # according to Thrift
        if thrift_type_data.field_type.type_parameters:
            name += "<%s>" % ", ".join([
                t.type_name()
                for t in thrift_type_data.field_type.type_parameters])
        return name


class ThriftFieldData(object):

    def __init__(
            self,
            is_optional=False):
        # This reflects the ternary logic of required-ness in Thrift.
        # If a field is not required, it's default, not optional.
        # Setting this makes it optional.
        # Note: the current python lib for thrift doesn't really
        # differentiate default and optional, so this will only make
        # a difference once we have thrift IDL generation.
        self.is_optional = is_optional
