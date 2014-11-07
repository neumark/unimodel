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

class JSONFieldData(object):

    def __init__(
            self,
            property_name=None):
        self.property_name = property_name                
 

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
