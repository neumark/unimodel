from unimodel.validation import (ValidationException, ValueTypeException)
from unimodel.validation import is_str

# --
# UTILITY FUNCTIONS
# --

def instantiate_if_class(t):
    # If they left off the parenthesis (eg: Field(Int)),
    # instantiate the type class.
    if isinstance(t, type):
        return t()
    return t

def type_id_to_type_constructor(type_id):
    import sys
    import inspect
    for obj_name in dir(sys.modules[__name__]):
        obj = getattr(sys.modules[__name__], obj_name)
        if inspect.isclass(obj) and issubclass(obj, FieldType) and getattr(obj, 'type_id', None) == type_id:
            return obj
    return None


def type_id_to_name_dict():
    import sys
    import inspect
    type_dict = {}
    for type_name in dir(sys.modules[__name__]):
        t = getattr(sys.modules[__name__], type_name)
        if inspect.isclass(t) and issubclass(
                t,
                FieldType) and hasattr(
                t,
                'type_id'):
            type_dict[t.type_id] = t.__name__.lower()
    return type_dict

def assert_type(python_type, value):
    if not issubclass(type(value), python_type):
        str_value = "<nonprintable value>"
        try:
            str_value = str(value)
        except:
            pass
        msg = "Expecting type %s, got %s instead (value was %s)" % (
            str(python_type),
            str(type(value)),
            str_value)
        raise ValueTypeException(msg)

# --
# Field types
# --

class StringTypeMarker(object):
    pass

class NumberTypeMarker(object):
    pass

class FieldType(object):
    # type_id is the unimodel type id, it should be set on child classes
    def __init__(
            self,
            type_parameters=None,
            metadata=None):
        if not type_parameters:
            type_parameters = []
        type_parameters_fixed = [
            instantiate_if_class(t) for t in type_parameters]
        self.type_parameters = type_parameters_fixed
        self.metadata = metadata

    def get_python_type(self):
        from unimodel.util import get_backend_type
        return get_backend_type("python", self.type_id)

    def run_custom_validators(self, value):
        # run custom validators (if any)
        if self.metadata and self.metadata.validators:
            for validator in self.metadata.validators:
                validator.validate(value)

    def validate(self, value):
        # check type of value
        assert_type(self.get_python_type(), value)
        self.run_custom_validators(value)

    def get_type_name(self):
        type_name = self.__class__.__name__
        type_parameter_names = [t.get_type_name() for t in self.type_parameters]
        if type_parameter_names:
            type_name = "%s(%s)" % (type_name, ", ".join(type_parameter_names))
        return type_name


class ParametricType(FieldType):

    def validate_elements(self, collection, field_type):
        ix = 0
        for elem in collection:
            try:
                field_type.validate(elem)
            except ValidationException as ex:
                msg = ("%(classname)s validation error in element number " +
                       "%(ix)s (value %(elem)s) %(ex_msg)s") % {
                    'classname': str(type(self)),
                    'ix': str(ix),
                    'elem': str(elem),
                    'ex_msg': str(ex)}
                # TODO: maybe try to raise the same exception with a new
                # message
                raise ValidationException(msg)
            ix += 1

    def validate(self, collection):
        super(ParametricType, self).validate(collection)
        self.validate_elements(collection, self.type_parameters[0])


# TODO: int range validation!
class Int64(FieldType, NumberTypeMarker):
    type_id = 1

Int = Int64  # default is 64 bit integers


class Int32(Int):
    type_id = 2

# Integers smaller than 32 bits descend from int32 to have
# the same json_type

class Int16(Int):
    type_id = 3

class Int8(Int):
    type_id = 4

class Enum(Int):
    type_id = 5

    def __init__(self, enum_dict, **kwargs):
        super(Enum, self).__init__(**kwargs)
        self.keys_to_names = enum_dict
        self.names_to_keys = {}
        for k, v in enum_dict.items():
            if not is_str(v):
                raise Exception("Enum names must be strings")
            if v in self.names_to_keys:
                raise Exception("Duplicate enum value: %s" % k)
            self.names_to_keys[v] = k

    def validate(self, value):
        super(Enum, self).validate(value)
        if not (value in self.keys_to_names.keys()):
            raise ValueTypeException(
                "%s is an invalid value for this enum. Valid values: %s" %
                (value, str(
                    self.keys_to_names)))

    def name_to_key(self, name):
        return self.names_to_keys[name]

    def names(self):
        return self.names_to_keys.keys()

    def key_to_name(self, key):
        return self.keys_to_names[key]


class Double(FieldType, NumberTypeMarker):
    type_id = 6

class Bool(FieldType):
    type_id = 7

class UTF8(FieldType, StringTypeMarker):
    type_id = 8

    def validate(self, value):
        # check type of value
        if not is_str(value):
            str_value = "<nonprintable value>"
            try:
                str_value = str(value)
            except:
                pass
            msg = "Expecting type string, got %s instead (value was %s)" % (
                str(type(value)),
                str_value)
            raise ValueTypeException(msg)
        self.run_custom_validators(value)


class Binary(UTF8, StringTypeMarker):
    type_id = 9

class Struct(FieldType):
    type_id = 10

    def __init__(self, struct_class, **kwargs):
        self.struct_class = struct_class
        super(Struct, self).__init__(**kwargs)

    def get_python_type(self):
        return self.struct_class

    def validate(self, value):
        assert_type(self.struct_class, value)
        value.validate()

# Tuples exist because they are defined / used in jsonschema.
# It is very easy to create non-backwards-compatible protocols
# using tuples. I do not recommend using them.


class Tuple(FieldType):
    type_id = 11

    def __init__(self, *type_parameters, **kwargs):
        super(Tuple, self).__init__(type_parameters=type_parameters, **kwargs)
        if len(type_parameters) == 0:
            raise Exception("Attempting to define empty Tuple")

    def validate(self, value):
        assert_type(tuple, value)
        if len(value) != len(self.type_parameters):
            raise ValueTypeException("Expecting %s length tuple, got %s" % (
                len(self.type_parameters), len(value)))
        [assert_type(t.get_python_type(), v) for t, v in zip(self.type_parameters, value)]


class List(ParametricType):
    type_id = 12

    def __init__(self, element_type, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.type_parameters = [instantiate_if_class(element_type)]


class Set(List):
    type_id = 13

class Map(ParametricType):
    type_id = 14

    def __init__(self, key_type, value_type, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        self.type_parameters = [
            instantiate_if_class(key_type),
            instantiate_if_class(value_type)]

    def validate(self, dictionary):
        # First run validators on the container type itself.
        super(Map, self).validate(dictionary)
        # Validate the elements of the container.
        if dictionary:
            self.validate_elements(dictionary.keys(), self.type_parameters[0])
            self.validate_elements(
                dictionary.values(),
                self.type_parameters[1])

class BigInt(FieldType, NumberTypeMarker):
    type_id = 15

    def to_string(self, value):
        return str(value)

    def from_string(self, string):
        return long(string)

class JSONData(FieldType):
    type_id = 16

    def to_string(self, value):
        import json
        return json.dumps(value)

    def from_string(self, string):
        import json
        return json.loads(string)

    def validate(self, dictionary):
        # we could theoretically walk the
        # json data to make sure only
        # json-serializable (non class instance)
        # values are within
        pass

