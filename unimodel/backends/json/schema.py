class StructType(object):
    DEFAULT=0
    UNBOXED=1
    FLATTENED=2

class JsonStructData(object):
    def __init__(
            self,
            struct_type=StructType.DEFAULT):
        self.struct_type = struct_type

class JSONSchemaWriter(object):
    pass
