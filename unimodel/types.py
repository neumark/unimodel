from unimodel.validation import (ValidationException, ValueTypeException)
from unimodel.backends.thrift.type_data import ThriftTypeData, TType
from unimodel.backends.json.type_data import JSONTypeData
from unimodel.metadata import Metadata
from unimodel.validation import is_str


def instantiate_if_class(t):
    # If they left off the parenthesis (eg: Field(Int)),
    # instantiate the type class.
    if isinstance(t, type):
        return t()
    return t


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

# Marker classes for types


class NumberType(object):
    pass


class FieldType(object):
    # type_id is the unimodel type id

    def __init__(
            self,
            type_id,
            python_type,
            type_parameters=None,
            metadata=None):
        self.type_id = type_id
        self.python_type = python_type
        if type_parameters:
            type_parameters_fixed = [
                instantiate_if_class(t) for t in type_parameters]
            self.type_parameters = type_parameters_fixed
        else:
            self.type_parameters = []
        self.metadata = metadata

    def run_custom_validators(self, value):
        # run custom validators (if any)
        if self.metadata.validators:
            for validator in self.metadata.validators:
                validator.validate(value)

    def validate(self, value):
        # check type of value
        assert_type(self.python_type, value)
        self.run_custom_validators(value)


class BasicType(FieldType):

    """Descendant classes must define
       - type_id
       - json_type
       - thrift_type_id
       - python_type
       to use this base class."""

    def __init__(self, **kwargs):
        super(
            BasicType,
            self).__init__(
            self.type_id,
            self.python_type,
            **kwargs)
        # This way metadata can be passed to the constructor of the type, but
        # if not, it's created here.
        self.metadata = self.metadata or Metadata()
        # Note: self.metadata.backend_data['thrift'] should be a ThriftTypeData
        # object
        if 'thrift' not in self.metadata.backend_data:
            self.metadata.backend_data['thrift'] = ThriftTypeData()
        self.metadata.backend_data['thrift'].type_id = self.thrift_type_id
        if 'json' not in self.metadata.backend_data:
            self.metadata.backend_data['json'] = JSONTypeData()
        self.metadata.backend_data['json'].type_name = self.json_type


class CollectionType(BasicType):

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
        super(CollectionType, self).validate(collection)
        self.validate_elements(collection, self.type_parameters[0])


# TODO: int range validation!
class Int64(BasicType, NumberType):
    type_id = 1
    python_type = int
    thrift_type_id = TType.I64
    json_type = "number"

Int = Int64  # default is 64 bit integers


class Int32(Int):
    type_id = 2
    thrift_type_id = TType.I32


class Int16(Int):
    type_id = 3
    thrift_type_id = TType.I16


class Int8(Int):
    type_id = 4
    thrift_type_id = TType.I08


class Enum(Int):
    type_id = 5
    json_type = "enum"
    thrift_type_id = TType.I64

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


class Double(BasicType, NumberType):
    type_id = 6
    python_type = float
    thrift_type_id = TType.DOUBLE
    json_type = "number"


class Bool(BasicType):
    type_id = 7
    python_type = bool
    thrift_type_id = TType.BOOL
    json_type = "boolean"


class UTF8(BasicType):
    type_id = 8
    python_type = str
    thrift_type_id = TType.STRING
    json_type = "string"

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


class Binary(UTF8):
    type_id = 9
    python_type = str
    thrift_type_id = TType.STRING
    json_type = "string"

    def __init__(self, **kwargs):
        super(Binary, self).__init__(**kwargs)
        self.metadata.backend_data['thrift'].is_binary = True


class Struct(BasicType):
    type_id = 10
    thrift_type_id = TType.STRUCT
    json_type = "object"

    def validate(self, value):
        super(Struct, self).validate(value)
        value.validate()

    def __init__(self, struct_class, **kwargs):
        self.python_type = struct_class
        super(Struct, self).__init__(**kwargs)

# Tuples exist because they are defined / used in jsonschema.
# It is very easy to create non-backwards-compatible protocols
# using tuples. I do not recommend using them.


class Tuple(Struct):
    type_id = 11
    json_type = "array"
    python_type = tuple

    def __init__(self, *args, **kwargs):
        super(Tuple, self).__init__(self.python_type, **kwargs)
        if len(args) == 0:
            raise Exception("Attempting to define empty Tuple")
        self.element_types = args
        self.metadata.backend_data['thrift'].is_tuple = True

    def validate(self, value):
        assert_type(tuple, value)
        if len(value) != len(self.element_types):
            raise ValueTypeException("Expecting %s length tuple, got %s" % (
                len(self.element_types), len(value)))
        [assert_type(t.python_type, v) for v in zip(self.element_types, value)]


class List(CollectionType):
    type_id = 12
    thrift_type_id = TType.LIST
    python_type = list
    json_type = "array"

    def __init__(self, element_type, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.type_parameters = [instantiate_if_class(element_type)]


class Set(List):
    type_id = 13
    python_type = set
    thrift_type_id = TType.SET


class Map(CollectionType):
    type_id = 14
    thrift_type_id = TType.MAP
    python_type = dict
    json_type = "object"

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
