class StructType(object):
    DEFAULT=0
    UNBOXED=1
    FLATTENED=2

class JSONStructData(object):

    def __init__(
            self,
            # struct_type influcences how Struct objects are mapped to dicts
            struct_type=StructType.DEFAULT,
            # allow_additional_fields only influences the jsonschema definition
            allow_additional_fields=True):
        self.struct_type = struct_type
        self.allow_additional_fields = allow_additional_fields

class JSONTypeData(object):
    
    def __init__(
            self,
            type_name=None):
        self.type_name = type_name
