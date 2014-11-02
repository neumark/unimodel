from thriftmodel.wireformat_thrift.type_info import ThriftTypeInfo, TType
from thriftmodel.validation import (ValidationException,
    ValueTypeException)

class FieldType(object):
    def __init__(self, python_type, thrift_type_info, type_parameters=None):
        self.python_type = python_type
        self.thrift_type_info = thrift_type_info
        type_parameters_fixed = []
        if type_parameters:
            for t in type_parameters:
                # If they left off the parenthesis, fix it.
                if type(t) == type:
                    t = t()
                type_parameters_fixed.append(t)
        self.type_parameters = type_parameters_fixed
        self.thrift_type_info.field_type = self

    def validate(self, value):
        if type(value) != self.python_type:
            msg = "Expecting type %s, got %s instead (value was %s)" % (
                str(self.python_type),
                str(type(value)),
                str(value))
            raise ValueTypeException(msg)

class CollectionType(FieldType):

    def validate_elements(self, collection, field_type):
        ix = 0
        for elem in collection:
            try:
                field_type.validate(elem)
            except ValidationException, ex:
                msg = "%(classname)s validation error in element number %(ix)s (value %(elem)s) %(ex_msg)s" % {
                        'classname': self.__class__.name,
                        'ix': str(ix),
                        'elem': str(elem),
                        'ex_msg': str(ex)}
                # TODO: maybe try to raise the same exception with a new message
                raise ValidationException(msg)
            ix += 1

    def validate(self, collection):
        super(CollectionType, self).validate(collection)
        self.validate_elements(collection, self.type_parameters[0])


class BasicType(FieldType):
    """Descendant classes must define thrift_type_id and python_type."""
    def __init__(self, thrift_type_kwargs=None):
        thrift_type_kwargs = thrift_type_kwargs or {}
        thrift_type_info = ThriftTypeInfo(self.thrift_type_id, **thrift_type_kwargs)
        super(BasicType, self).__init__(self.python_type, thrift_type_info)

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
    # TODO: unicode types for python2
    python_type = str
    thrift_type_id = TType.STRING

class Binary(UTF8):
    python_type = str
    thrift_type_id = TType.STRING
    def __init__(self, thrift_type_kwargs=None):
        thrift_type_kwargs = thrift_type_kwargs or {}
        thrift_type_kwargs['is_binary'] = True
        super(Binary, self).__init__(thrift_type_kwargs)


class Struct(BasicType):
    thrift_type_id = TType.STRUCT
    def __init__(self, struct_class, thrift_type_kwargs=None):
        self.python_type = struct_class
        thrift_type_kwargs = thrift_type_kwargs or {}
        super(Struct, self).__init__(thrift_type_kwargs)

class Union(Struct):
    def __init__(self, *args, **kwargs):
        super(Union, self).__init__(*args, **kwargs)
        self.thrift_type_info.is_union = True

class List(CollectionType):
    thrift_type_id = TType.LIST

    def __init__(self, element_type, thrift_type_kwargs=None):
        type_parameters = [element_type]
        thrift_type_kwargs = thrift_type_kwargs or {}
        thrift_type_info = ThriftTypeInfo(self.thrift_type_id, **thrift_type_kwargs)
        super(List, self).__init__(list, thrift_type_info, type_parameters=type_parameters)


class Set(List):
    thrift_type_id = TType.SET

class Map(CollectionType):
    thrift_type_id = TType.MAP

    def __init__(self, key_type, value_type, thrift_type_kwargs=None):
        type_parameters = [key_type, value_type]
        thrift_type_kwargs = thrift_type_kwargs or {}
        thrift_type_info = ThriftTypeInfo(self.thrift_type_id, **thrift_type_kwargs)
        super(Map, self).__init__(dict, thrift_type_info, type_parameters=type_parameters)

    def validate(self, dictionary):
        # First run validators on the container type itself.
        super(Map, self).validate(dictionary)
        # Validate the elements of the container.
        if dictionary:
            self.validate_elements(dictionary.keys(), self.type_parameters[0])
            self.validate_elements(dictionary.values(), self.type_parameters[1])
