import sys
import types
import itertools
from functools import wraps
from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from thrift.protocol.TBase import TBase, TExceptionBase
from thrift.transport import TTransport
from thriftmodel.protocol import default_protocol_factory
class ValidationException(Exception):
    pass

class UndefinedFieldException(Exception):
    pass

class ProtocolDebugger(object):
    def __init__(self, protocol_factory,stream=sys.stdout, log_protocol=True, log_transport=True):
        self.protocol_factory = protocol_factory
        self.log_protocol = log_protocol
        self.log_transport = log_transport
        self.stream = stream
        self.indent_counter = 0
        self.call_counter = 0

    def wrap_method(self, obj, class_name, function_name, func):
        # print call id so we can sort
        # indent_counter a single value, not per obj
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.indent_counter += 1
            current_call_counter = self.call_counter
            self.call_counter += 1
            str_args = ["%s" % str(a) for a in args] + ["%s=%s" % (str(k), str(v)) for k,v in kwargs.iteritems()]
            response = func(*args, **kwargs)
            self.indent_counter -= 1
            self.stream.write("%04d %s%s.%s(%s) -> %s\n" % (current_call_counter, " " * self.indent_counter, class_name, function_name, ", ".join(str_args), response))
            return response
        return wrapper

    def getProtocol(self, transport):
        protocol = self.protocol_factory.getProtocol(transport)
        objects_to_patch = []
        if self.log_protocol:
            objects_to_patch.append(protocol)
        if self.log_transport:
            objects_to_patch.append(transport)
        for obj in objects_to_patch:
            for name in dir(obj):
                fn = getattr(obj, name)
                if hasattr(fn, '__call__'):
                    setattr(obj, name, self.wrap_method(obj, obj.__class__.__name__, name, fn))
        return protocol


class ThriftField(object):
    _field_creation_counter = 0

    def __init__(self, field_type_id,
            thrift_field_name=None,
            field_id=-1,
            default=None,
            required=False):
        self.creation_count = ThriftField._field_creation_counter
        ThriftField._field_creation_counter += 1
        self.field_type_id = field_type_id
        self.thrift_field_name = thrift_field_name
        self.default = default
        self.field_id = field_id
        self.required=required

    def to_tuple(self):
        return (self.field_id, self.field_type_id, self.thrift_field_name, None, self.default,)

class ParametricThriftField(ThriftField):
    def __init__(self, field_type_id, type_parameter, **kwargs):
        super(ParametricThriftField, self).__init__(field_type_id, **kwargs)
        self.type_parameter = type_parameter

    def get_type_parameter(self):
        return self.type_parameter.to_tuple()[3] or None

    def to_tuple(self):
        return (self.field_id, self.field_type_id, self.thrift_field_name, self.get_type_parameter(), self.default,)

class IntField(ThriftField):
    def __init__(self, **kwargs):
        super(IntField, self).__init__(TType.I64, **kwargs)

class BoolField(ThriftField):
    def __init__(self, **kwargs):
        super(BoolField, self).__init__(TType.BOOL, **kwargs)

class UTF8Field(ThriftField):
    def __init__(self, **kwargs):
        super(UTF8Field, self).__init__(TType.UTF8, **kwargs)

class StringField(ThriftField):
    def __init__(self, **kwargs):
        super(StringField, self).__init__(TType.STRING, **kwargs)

class StructField(ParametricThriftField):
    def __init__(self, type_parameter, **kwargs):
        super(StructField, self).__init__(TType.STRUCT, type_parameter, **kwargs)

class ListField(ParametricThriftField):
    def __init__(self, type_parameter, **kwargs):
        super(ListField, self).__init__(TType.LIST, type_parameter, **kwargs)
    def get_type_parameter(self):
        tp = self.type_parameter.to_tuple()
        return (tp[1], tp[3])

class MapField(ParametricThriftField):
    def __init__(self, key_type_parameter, value_type_parameter, **kwargs):
        super(MapField, self).__init__(TType.MAP, None, **kwargs)
        self.key_type_parameter = key_type_parameter
        self.value_type_parameter = value_type_parameter

    def get_type_parameter(self):
        key_spec = self.key_type_parameter.to_tuple()
        value_spec = self.value_type_parameter.to_tuple()
        return (key_spec[1],
                key_spec[3],
                value_spec[1],
                value_spec[3])


def serialize_simplejson(obj):
    return serialize(obj, protocol_factory=TJSONProtocol.TSimpleJSONProtocolFactory())

def serialize_debug_simplejson(obj):
    return serialize(obj, protocol_factory=ProtocolDebugger(TJSONProtocol.TSimpleJSONProtocolFactory()))

def serialize_json(obj):
    return serialize(obj, protocol_factory=TJSONProtocol.TJSONProtocolFactory())

def serialize_compact(obj):
    return serialize(obj, protocol_factory=TCompactProtocol.TCompactProtocolFactory())

def serialize(obj, protocol_factory=default_protocol_factory):
    transport = TTransport.TMemoryBuffer()
    protocol = protocol_factory.getProtocol(transport)
    write_to_stream(obj, protocol)
    transport._buffer.seek(0)
    return transport._buffer.getvalue()

def deserialize(cls, stream, protocol_factory=default_protocol_factory):
    obj = cls()
    transport = TTransport.TMemoryBuffer()
    transport._buffer.write(stream)
    transport._buffer.seek(0)
    protocol = protocol_factory.getProtocol(transport)
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
        cls.make_thrift_spec(fields)

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
        if name in fields_by_name:
            model_data = object.__getattribute__(self, '_model_data')
            return model_data.get(fields_by_name[name].field_id, None)
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

    def serialize(self, protocol_factory=default_protocol_factory):
        return serialize(self, protocol_factory)

    def _set_value_by_thrift_field_id(self, field_id, value):
        self._model_data[field_id] = value

    @classmethod
    def deserialize(cls, stream, protocol_factory=default_protocol_factory):
        return deserialize(cls, stream, protocol_factory)

    @classmethod
    def make_thrift_spec(cls, field_dict):
        # TODO: if cls._fields already exists, extend it instead of replacing it.
        # sort dict by field creation order
        fields = sorted([(k,v) for k,v in field_dict.iteritems()],
            key=lambda x:x[1].creation_count)
        # set missing field names
        for name, field_data in fields:
            if field_data.thrift_field_name is None:
                field_data.thrift_field_name = name
        # reuse existing thrift_spec if possible
        if not hasattr(cls, 'thrift_spec'):
            cls.thrift_spec = [None]
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
        if cls.thrift_spec != thrift_spec_list:
            cls.thrift_spec = tuple(thrift_spec_list)
        # set helper dicts on class so field definitions can be accessed easily
        cls._fields_by_id = dict([(v.field_id, (k,v)) for k,v in fields])
        cls._fields_by_name = dict([(k,v) for k,v in fields])

    @classmethod
    def to_tuple(cls):
        return (-1, TType.STRUCT, cls.__name__, (cls, cls.thrift_spec), None,)

    def validate(self):
        # check to make sure required fields are set
        for k, v in self._fields_by_name.iteritems():
            if v.required and self._model_data.get(v.field_id, None) is None:
                raise ValidationException("Required field %s (id %s) not set" % (k, v.field_id))

class RecursiveThriftModel(ThriftModel):
    thrift_spec = [None]
