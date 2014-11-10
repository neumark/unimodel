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
