# This file is for classes holding Thrift-specific data for types and fields.
# Since this is imported form unimodel/types.py, it's important not to
# import the whole apache thrift python lib from this file.
# Instead the TType class is duplicated here.

class TType:
  STOP   = 0
  VOID   = 1
  BOOL   = 2
  BYTE   = 3
  I08    = 3
  DOUBLE = 4
  I16    = 6
  I32    = 8
  I64    = 10
  STRING = 11
  UTF7   = 11
  STRUCT = 12
  MAP    = 13
  SET    = 14
  LIST   = 15
  UTF8   = 16
  UTF16  = 17

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
            is_union=False):
        self.field_type = None  # set to reference FieldType object in BasicType constructor
        self.type_id = type_id
        self.is_binary = is_binary
        self.is_union = is_union

    def type_name(self):
        name = TType._VALUES_TO_NAMES[self.type_id].lower()
        if name == "string" and self.is_binary:
            name = "binary"
        if name == "struct" and self.is_union:
            name = "union"
        if self.field_type.type_parameters:
            name += "<%s>" % ", ".join([t.type_name() for t in self.field_type.type_parameters])
        return name

class ThriftFieldData(object):

    def __init__(
            self,
            is_optional=False):
        self.is_optional = is_optional
