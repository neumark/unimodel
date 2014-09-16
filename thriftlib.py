import sys
import types
from functools import wraps
from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from thrift.protocol.TBase import TBase, TExceptionBase
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TCompactProtocol, TJSONProtocol
"""

struct A {
    1: i64 a,
    2: BannedClient c,
    3: i64 d=6,
    4: list<string> e,
    5: list<BannedClient> f
    6: map<i64, string> g
    7: list<map<i64, list<BannedClient>>> h
}

 compiles to:

  thrift_spec = (
    None, # 0
    (1, TType.I64, 'a', None, None, ), # 1
    (2, TType.STRUCT, 'c', (BannedClient, BannedClient.thrift_spec), None, ), # 2
    (3, TType.I64, 'd', None, 6, ), # 3
    (4, TType.LIST, 'e', (TType.STRING,None), None, ), # 4
    (5, TType.LIST, 'f', (TType.STRUCT,(BannedClient, BannedClient.thrift_spec)), None, ), # 5
    (6, TType.MAP, 'g', (TType.I64,None,TType.STRING,None), None, ), # 6
    (7, TType.LIST, 'h', (TType.MAP,(TType.I64,None,TType.LIST,(TType.STRUCT,(BannedClient, BannedClient.thrift_spec)))), None, ), # 7
  )
"""

class Protocol(object):

    factories = [
        ('binary', TBinaryProtocol.TBinaryProtocolFactory()),
        ('json', TJSONProtocol.TJSONProtocolFactory()),
        ('simple_json', TJSONProtocol.TSimpleJSONProtocolFactory()),
        ('compact', TCompactProtocol.TCompactProtocolFactory())
    ]

    @classmethod
    def lookup_by_id(cls, protocol_id):
        return (protocol_id, ) + cls.factories[protocol_id]

    @classmethod
    def lookup_by_name(cls, protocol_name):
        for i in xrange(0, len(cls.factories)):
            if cls.factories[i][0] == protocol_name:
                return (i, ) + cls.factories[i]
        return None

    def __init__(self, protocol_name_or_id):
        if type(protocol_name_or_id) == int:
            protocol = self.lookup_by_id(protocol_name_or_id)
        else:
            protocol = self.lookup_by_name(protocol_name_or_id)
        self.id, self.name, self.factory =  protocol


class UndefinedFieldException(Exception):
    pass

class DynamicClassNotFoundException(Exception):
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

    def __init__(self, field_type_id, thrift_field_name=None, field_id=-1, default=None):
        self.creation_count = ThriftField._field_creation_counter
        ThriftField._field_creation_counter += 1
        self.field_type_id = field_type_id
        self.thrift_field_name = thrift_field_name
        self.default = default
        self.field_id = field_id

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
        return (self.key_type_parameter.thrift_field_name,
                self.key_type_parameter.to_tuple()[1:],
                self.value_type_parameter.thrift_field_name,
                self.value_type_parameter.to_tuple()[1:])


def serialize_simplejson(obj):
    return serialize(obj, protocol_factory=TJSONProtocol.TSimpleJSONProtocolFactory())

def serialize_debug_simplejson(obj):
    return serialize(obj, protocol_factory=ProtocolDebugger(TJSONProtocol.TSimpleJSONProtocolFactory()))

def serialize_json(obj):
    return serialize(obj, protocol_factory=TJSONProtocol.TJSONProtocolFactory())

def serialize_compact(obj):
    return serialize(obj, protocol_factory=TCompactProtocol.TCompactProtocolFactory())

def serialize(obj, protocol_factory):
    transport = TTransport.TMemoryBuffer()
    protocol = protocol_factory.getProtocol(transport)
    write_to_stream(obj, protocol)
    transport._buffer.seek(0)
    return transport._buffer.getvalue()

def deserialize(cls, stream, protocol_factory):
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
            field_name = self.thrift_spec[i+1][2]
            setattr(self, field_name, args[i])

    def __repr__(self):
        L = ['%s=%r' % (self._fields_by_id[field_id][0], value)
            for field_id, value in self._model_data.iteritems()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

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

    def serialize(self, protocol_factory=TBinaryProtocol.TBinaryProtocolFactory()):
        return serialize(self, protocol_factory)

    def _set_value_by_thrift_field_id(self, field_id, value):
        self._model_data[field_id] = value

    @classmethod
    def deserialize(cls, stream, protocol_factory=TBinaryProtocol.TBinaryProtocolFactory()):
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

class RecursiveThriftModel(ThriftModel):
    thrift_spec = [None]

class DynamicObject(ThriftModel):
    protocol = ThriftField(TType.I16)
    class_name = StringField()
    data = StringField()

    @classmethod
    def from_object(cls, obj, protocol_name_or_id=0):
        protocol = Protocol(protocol_name_or_id)
        return cls(protocol.id, obj.__class__.__name__, obj.serialize(protocol.factory))

    def unpack(self, class_hint=None, module_hint=None):
        if class_hint is not None:
            cls = class_hint
        else:
            dict_candidates = []
            if module_hint is not None:
                dict_candidates.append(sys.modules[module_hint].__dict__)
            else:
                # Use the locals of the calling stack frame
                dict_candidates.append(sys._getframe(1).f_locals)
            dict_candidates.append(globals())
            for candidate in dict_candidates:
                cls = candidate.get(self.class_name, None)
                if cls is not None:
                    return cls.deserialize(self.data, Protocol(self.protocol).factory)
        raise DynamicClassNotFoundException(self.class_name)
