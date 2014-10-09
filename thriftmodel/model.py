import sys
import types
import itertools
import inspect
from functools import wraps
from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from thrift.protocol.TBase import TBase, TExceptionBase
from thrift.transport import TTransport
from thriftmodel.protocol import default_protocol_factory

class ValidationException(Exception):
    pass

class UndefinedFieldException(Exception):
    pass

def thrift_field_id_to_name(field_type_id):
    return TType._VALUES_TO_NAMES[field_type_id].lower()

class ThriftField(object):
    _field_creation_counter = 0

    def __init__(self,
            thrift_field_name=None,
            field_id=-1,
            field_type_id=-1,
            default=None,
            required=False,
            validators=None):
        self.creation_count = ThriftField._field_creation_counter
        ThriftField._field_creation_counter += 1
        self.field_id = field_id
        self.thrift_field_name = thrift_field_name
        self.default = default
        # if the field_type_id argument is invalid, we can use the
        # default value set on the class (when it exists).
        if field_type_id < 0 and hasattr(self.__class__, 'field_type_id'):
            self.field_type_id = self.__class__.field_type_id
        else:
            # TODO: we should probably throw an exception here
            # if field_type_id is < 0
            self.field_type_id = field_type_id
        self.required=required
        self.validators = validators

    def validate(self, value):
        for validator in (self.validators or []):
            # TODO: we may want to save the output of validators for warnings and messages
            validator.validate(value)

    def thrift_type_name(self):
        return thrift_field_id_to_name(self.field_type_id)

    def to_tuple(self):
        return (self.field_id, self.field_type_id, self.thrift_field_name, None, self.default,)


class ParametricThriftField(ThriftField):
    def __init__(self, type_parameter, **kwargs):
        super(ParametricThriftField, self).__init__(**kwargs)
        self.type_parameter = type_parameter

    def get_type_parameter(self):
        tp = self.type_parameter.to_tuple()
        return (tp[1], tp[3])

    def _validate_elements(self, collection, field_or_model):
        if field_or_model is not None:
            if isinstance(field_or_model, ThriftField):
                for elem in collection:
                    field_or_model.validate(elem)
            if isinstance(field_or_model, ThriftModel):
                for elem in collection:
                    elem.validate()

    def validate(self, container):
        # Run an validators on the container type itself.
        # Eg: if we want to chech that a list has 4 elements,
        # the validator would be on the list itself.
        super(ParametricThriftField, self).validate(container)
        # Validate the elements of the container if there are validators defined.
        self._validate_elements(container, self.type_parameter)

    def thrift_type_name(self):
        return "%s<%s>" % (
            thrift_field_id_to_name(self.field_type_id),
            self.type_parameter.thrift_type_name())

    def to_tuple(self):
        return (self.field_id, self.field_type_id, self.thrift_field_name, self.get_type_parameter(), self.default,)

class IntField(ThriftField):
    field_type_id = TType.I64

class DoubleField(ThriftField):
    field_type_id = TType.DOUBLE

class BoolField(ThriftField):
    field_type_id = TType.BOOL

class UTF8Field(ThriftField):
    field_type_id = TType.UTF8

class StringField(ThriftField):
    field_type_id = TType.STRING

class BinaryField(StringField):
    is_binary = True

class StructField(ParametricThriftField):
    field_type_id = TType.STRUCT

    def thrift_type_name(self):
        return self.type_parameter.thrift_type_name()

    def get_type_parameter(self):
        return self.type_parameter.to_tuple()[3]

class UnionField(StructField):
    is_union = True
    def __init__(self, type_parameter, **kwargs):
        super(UnionField, self).__init__(type_parameter, is_boxed=False, **kwargs)
        self.is_boxed = is_boxed

class ListField(ParametricThriftField):
    field_type_id = TType.LIST

    def get_type_parameter(self):
        tp = self.type_parameter.to_tuple()
        return (tp[1], tp[3])

class SetField(ListField):
    field_type_id = TType.SET

class MapField(ParametricThriftField):
    field_type_id = TType.MAP

    def __init__(self, key_type_parameter, value_type_parameter, **kwargs):
        super(MapField, self).__init__(None, **kwargs)
        self.key_type_parameter = key_type_parameter
        self.value_type_parameter = value_type_parameter

    def get_type_parameter(self):
        key_spec = self.key_type_parameter.to_tuple()
        value_spec = self.value_type_parameter.to_tuple()
        return (key_spec[1],
                key_spec[3],
                value_spec[1],
                value_spec[3])

    def validate(self, dictionary):
        # Run an validators on the container type itself.
        # Eg: if we want to chech that a list has 4 elements,
        # the validator would be on the list itself.
        super(MapField, self).validate(dictionary)
        # Validate the elements of the container if there are validators defined.
        if dictionary:
            self._validate_elements(dictionary.keys(), self.key_type_parameter)
            self._validate_elements(dictionary.values(), self.value_type_parameter)

    def thrift_type_name(self):
        return "%s<%s, %s>" % (
            thrift_field_id_to_name(self.field_type_id),
            self.key_type_parameter.thrift_type_name(),
            self.value_type_parameter.thrift_type_name())

def serialize(obj, protocol_factory=default_protocol_factory, protocol_options=None):
    transport = TTransport.TMemoryBuffer()
    protocol = protocol_factory.getProtocol(transport)
    if protocol_options is not None and hasattr(protocol, 'set_options'):
        protocol.set_options(protocol_options)
    write_to_stream(obj, protocol)
    transport._buffer.seek(0)
    return transport._buffer.getvalue()

def deserialize(cls, stream, protocol_factory=default_protocol_factory, protocol_options=None):
    obj = cls()
    transport = TTransport.TMemoryBuffer()
    transport._buffer.write(stream)
    transport._buffer.seek(0)
    protocol = protocol_factory.getProtocol(transport)
    if protocol_options is not None and hasattr(protocol, 'set_options'):
        protocol.set_options(protocol_options)
    read_from_stream(obj, protocol)
    return obj

def write_to_stream(obj, protocol):
    return protocol.writeStruct(obj, obj.thrift_spec)

def read_from_stream(obj, protocol):
    protocol.readStruct(obj, obj.thrift_spec)

class ThriftModelMetaclass(type):
    def __init__(cls, name, bases, dct):
        super(ThriftModelMetaclass, cls).__init__(name, bases, dct)
        fields = dict([(k,v) for k,v in dct.iteritems() if isinstance(v, ThriftField)])
        cls.apply_thrift_spec(fields)

class ThriftModel(TBase):

    __metaclass__ = ThriftModelMetaclass
    thrift_spec = (None,)

    def __init__(self, *args, **kwargs):
        self._model_data = {}

        for field_name, value in kwargs.iteritems():
            setattr(self, field_name, value)

        for i in xrange(0, len(args)):
            field_id = self.thrift_spec[i+1][0]
            self._model_data[field_id] = args[i]

    def __repr__(self):
        L = ['%s=%r' % (self._fields_by_id[field_id][0], value)
            for field_id, value in self._model_data.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

    def iterkeys(self):
        return itertools.imap(
                lambda pair: self._fields_by_id[pair[0]][1].thrift_field_name,
                itertools.ifilter(lambda pair: pair[1] is not None, self._model_data.iteritems()))

    def _thrift_field_name_to_field_id(self, thrift_field_name):
        field = [f[1] for f in self._fields_by_id.values() if f[1].thrift_field_name == thrift_field_name]
        if len(field) < 1:
            raise KeyError(thrift_field_name)
        return field[0].field_id

    def __getitem__(self, thrift_field_name):
        return self._model_data[self._thrift_field_name_to_field_id(thrift_field_name)]

    def __setitem__(self, thrift_field_name, value):
        self._model_data[self._thrift_field_name_to_field_id(thrift_field_name)] = value

    def __delitem__(self, thrift_field_name):
        self._model_data.__delitem__(
                self._thrift_field_name_to_field_id(thrift_field_name))

    def __iter__(self):
        return self.iterkeys()

    def __getattribute__(self, name):
        # check in model_data first
        fields_by_name = object.__getattribute__(self, '_fields_by_name')
        # Note: In a try ... raise block because reading of _model_data
        # raises an AttributeError in ThriftModel.__init__, when the
        # attribute is initialized.
        try:
            model_data = object.__getattribute__(self, '_model_data')
            # If a model field name matches, return its value
            if name in fields_by_name:
                return model_data.get(fields_by_name[name].field_id, None)
            # if a thrift field name matches, return its value
            field_candidates = [v for v in fields_by_name.values() if v.thrift_field_name == name]
            if len(field_candidates) > 0:
                return model_data.get(field_candidates[0].field_id, None)
        except AttributeError:
            pass
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name in self._fields_by_name:
            self._model_data[self._fields_by_name[name].field_id] = value
        else:
            object.__setattr__(self, name, value)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def serialize(self, protocol_factory=default_protocol_factory, protocol_options=None):
        return serialize(self, protocol_factory, protocol_options)

    def _set_value_by_thrift_field_id(self, field_id, value):
        self._model_data[field_id] = value

    def _get_value_by_thrift_field_id(self, field_id):
        return self._model_data.get(field_id, None)


    @classmethod
    def deserialize(cls, stream, protocol_factory=default_protocol_factory, protocol_options=None):
        return deserialize(cls, stream, protocol_factory, protocol_options)

    @classmethod
    def _convert_field_thrift_spec_to_thriftmodel(cls, thrift_spec):
        # verify that the id and name of the field is set
        return None  # TODO

    @classmethod
    def _get_inherited_fields_from_thrift_spec(cls, thrift_spec):
        thrift_spec_fields = []
        for field_thrift_spec in thrift_spec[1:]:
            converted_field = cls._convert_field_thrift_spec_to_thriftmodel(field_thrift_spec)
            thrift_spec_fields.append(converted_field)
        return thrift_spec_fields

    @classmethod
    def _get_inherited_fields(cls):
        # Inherited fields can come from cls.thrift_spec or
        # cls._fields_by_name
        # note that once make_thrift_spec() has run, this
        # will also return the fields of the current class.
        inherited_fields = {}  # id -> field model def
        thrift_spec = []
        if hasattr(cls, 'thrift_spec'):
            thrift_spec = cls.thrift_spec
        thrift_spec_fields = cls._get_inherited_fields_from_thrift_spec(thrift_spec)

    @classmethod
    def _field_dict_to_field_list(cls, field_dict):
        """ Return a sorted list of fields based on
            field creation order, setting field names."""
        # Then, we process the contents of field_dict
        fields = sorted([(k,v) for k,v in field_dict.iteritems()],
            key=lambda x:x[1].creation_count)
        # set missing field names
        for name, field_data in fields:
            if field_data.thrift_field_name is None:
                field_data.thrift_field_name = name
        return fields

    @classmethod
    def apply_thrift_spec(cls, fields):
        thrift_spec_attr = cls.make_thrift_spec(fields)
        for attr_name, attr_value in thrift_spec_attr.items():
            setattr(cls, attr_name, attr_value)


    @classmethod
    def make_thrift_spec(cls, field_dict):
        """ Returns a dictionary of attributes which will
            be set on the class by the metaclass. These
            attributes are:
            _fields_by_id
            _fields_by_name
            thrift_spec
        """
        # TODO: if cls._fields already exists, extend it instead of replacing it.
        fields = cls._field_dict_to_field_list(field_dict)
        # reuse existing thrift_spec if possible
        if not hasattr(cls, 'thrift_spec'):
            thrift_spec_list = [None]
        else:
            if type(cls.thrift_spec) == list:
                thrift_spec_list = cls.thrift_spec
            else:
                thrift_spec_list = list(cls.thrift_spec)
        # replace -1 field ids with the next available positive integer
        taken_field_ids = set([f[0] for f in cls.thrift_spec[1:]])
        next_field_id = 1
        for f in fields:
            field_tuple = f[1].to_tuple()
            if field_tuple[0] < 1:
                while next_field_id in taken_field_ids:
                    next_field_id += 1
                taken_field_ids.add(next_field_id)
                field_tuple = (next_field_id,) + field_tuple[1:]
            # update the field definition if the field_id has changed
            f[1].field_id = field_tuple[0]
            thrift_spec_list.append(field_tuple)
        # thrift_spec can be a list or a tuple
        # we only need to set it here in the latter case
        attr_dict = {}
        if cls.thrift_spec != thrift_spec_list:
            attr_dict['thrift_spec'] = tuple(thrift_spec_list)
        # set helper dicts on class so field definitions can be accessed easily
        attr_dict['_fields_by_id'] = dict([(v.field_id, (k,v)) for k,v in fields])
        attr_dict['_fields_by_name'] = dict([(k,v) for k,v in fields])
        return attr_dict

    @classmethod
    def to_tuple(cls):
        return (-1, TType.STRUCT, cls.__name__, (cls, cls.thrift_spec), None,)

    def validate(self):
        # check to make sure required fields are set
        for k, v in self._fields_by_name.iteritems():
            if v.required and self._model_data.get(v.field_id, None) is None:
                raise ValidationException("Required field %s (id %s) not set" % (k, v.field_id))
            # Run any field validators
            v.validate(self._model_data.get(v.field_id, None))
        # Run the validator for the model itself (if it is set)
        if hasattr(self, 'validators'):
            for validator in (self.validators or []):
                validator.validate(self)

class RecursiveThriftModel(ThriftModel):
    thrift_spec = [None]

class UnboxedUnion(object):
    is_unboxed_union = True

def collect_field_type_constructors():
    cons_list = {}
    for key in dir(sys.modules[__name__]):
        value = getattr(sys.modules[__name__], key)
        if inspect.isclass(value) and\
            issubclass(value, ThriftField) and\
            hasattr(value, "field_type_id"):
            cons_list[value.field_type_id] = value
    return cons_list
