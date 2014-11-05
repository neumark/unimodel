from unimodel.validation import (ValidationException, ValueTypeException)
from unimodel.backends.thrift.data import ThriftTypeData, TType
from unimodel.metadata import Metadata

def instantiate_if_class(t):
    # If they left off the parenthesis (eg: Field(Int)),
    # instantiate the type class.
    if type(t) == type:
        return t()
    return t

class FieldType(object):
    def __init__(self, python_type, type_parameters=None, metadata=None):
        self.python_type = python_type
        if type_parameters:
            type_parameters_fixed = [instantiate_if_class(t) for t in type_parameters]
            self.type_parameters = type_parameters_fixed
        else:
            self.type_parameters = []
        self.metadata = metadata

    def validate(self, value):
        # check type of value
        if type(value) != self.python_type:
            msg = "Expecting type %s, got %s instead (value was %s)" % (
                str(self.python_type),
                str(type(value)),
                str(value))
            raise ValueTypeException(msg)
        # run custom validators (if any)
        if self.metadata.validators:
            for validator in self.metadata.validators:
                validator.validate(value)

class BasicType(FieldType):
    """Descendant classes must define thrift_type_id and python_type."""
    def __init__(self, *args, **kwargs):
        super(BasicType, self).__init__(self.python_type, *args, **kwargs)
        # This way metadata can be passed to the constructor of the type, but
        # if not, it's created here.
        self.metadata = self.metadata or Metadata()
        # Note: self.metadata.backend_data['thrift'] should be a ThriftTypeData object
        if 'thrift' not in self.metadata.backend_data:
            self.metadata.backend_data['thrift'] = ThriftTypeData()
        self.metadata.backend_data['thrift'].type_id = self.thrift_type_id

class CollectionType(BasicType):

    def validate_elements(self, collection, field_type):
        ix = 0
        for elem in collection:
            try:
                field_type.validate(elem)
            except ValidationException, ex:
                msg = "%(classname)s validation error in element number %(ix)s (value %(elem)s) %(ex_msg)s" % {
                        'classname': str(type(self)),
                        'ix': str(ix),
                        'elem': str(elem),
                        'ex_msg': str(ex)}
                # TODO: maybe try to raise the same exception with a new message
                raise ValidationException(msg)
            ix += 1

    def validate(self, collection):
        super(CollectionType, self).validate(collection)
        self.validate_elements(collection, self.type_parameters[0])


class Int(BasicType):
    python_type = int
    thrift_type_id = TType.I64

class Double(BasicType):
    python_type = float
    thrift_type_id = TType.DOUBLE

class Bool(BasicType):
    python_type = bool
    thrift_type_id = TType.BOOL

class UTF8(BasicType):
    # TODO: unicode types for python2 fail validation
    python_type = str
    thrift_type_id = TType.STRING

class Binary(UTF8):
    python_type = str
    thrift_type_id = TType.STRING
    def __init__(self, *args, **kwargs):
        super(Binary, self).__init__(*args, **kwargs)
        self.metadata.backend_data['thrift'].is_binary = True

class Struct(BasicType):
    thrift_type_id = TType.STRUCT
    def __init__(self, struct_class, *args, **kwargs):
        self.python_type = struct_class
        super(Struct, self).__init__(*args, **kwargs)

class Union(Struct):
    def __init__(self, *args, **kwargs):
        super(Union, self).__init__(*args, **kwargs)
        self.metadata.backend_data['thrift'].is_union = True

class List(CollectionType):
    thrift_type_id = TType.LIST
    python_type = list

    def __init__(self, element_type, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.type_parameters = [instantiate_if_class(element_type)]

class Set(List):
    thrift_type_id = TType.SET

class Map(CollectionType):
    thrift_type_id = TType.MAP
    python_type = dict

    def __init__(self, key_type, value_type, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        self.type_parameters = [instantiate_if_class(key_type), instantiate_if_class(value_type)]

    def validate(self, dictionary):
        # First run validators on the container type itself.
        super(Map, self).validate(dictionary)
        # Validate the elements of the container.
        if dictionary:
            self.validate_elements(dictionary.keys(), self.type_parameters[0])
            self.validate_elements(dictionary.values(), self.type_parameters[1])
