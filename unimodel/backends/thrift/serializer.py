from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.protocol.TCompactProtocol import TCompactProtocol
from thrift.protocol.TJSONProtocol import TJSONProtocol
from thrift.transport import TTransport
from thrift.protocol.TBase import TBase
from unimodel.model import Unimodel, Field
from unimodel.backends.base import Serializer
from unimodel import types
from unimodel.util import get_backend_type
from contextlib import contextmanager
import json

class ThriftSpecFactory(object):

    def __init__(self, model_registry=None):
        self.model_registry = model_registry
        if self.model_registry is None:
            from unimodel.model import ModelRegistry
            self.model_registry = ModelRegistry()
        self._spec_cache = {}
        self.tuple_type_cache = {}

    def get_spec(self, struct_class):
        if struct_class not in self._spec_cache:
            self._spec_cache[
                struct_class] = self.get_spec_for_struct(struct_class)
        return self._spec_cache[struct_class]

    def get_spec_for_struct(self, struct_class):
        field_list = sorted(
            struct_class.get_field_definitions(),
            key=lambda x: x.field_id)
        thrift_spec = [None]
        # save the spec to cache so recurisve data structures work.
        self._spec_cache[struct_class] = thrift_spec
        for f in field_list:
            thrift_spec.append(self.get_spec_for_field(f))
        return thrift_spec

    def get_tuple_type_parameter(self, field_type):
        # tuple_id =
        #    (implementation_class, self.get_spec(implementation_class))
        ta = ThriftTupleAdapter(Field(field_type), None)
        return (ta.tuple_struct_class, self.get_spec(ta.tuple_struct_class))


    def get_spec_type_parameter(self, field_type):
        """ Returns value 3 of the element
            in thrift_spec which defines this field. """
        # tuples are encoded as structs
        if isinstance(field_type, types.Tuple):
            return self.get_tuple_type_parameter(field_type)
        # structs are a special case
        if isinstance(field_type, types.Struct):
            interface_class = field_type.get_python_type()
            implementation_class = self.model_registry.lookup(interface_class)
            return (implementation_class, self.get_spec(implementation_class))
        # If there are no type parameters, return None
        if not field_type.type_parameters:
            return None
        # lists, sets, maps
        spec_list = []
        for t in field_type.type_parameters:
            # for each type_parameter, first add the type's id
            spec_list.append(get_backend_type("thrift", t.type_id))
            # then the type's parameters
            spec_list.append(self.get_spec_type_parameter(t))
        return spec_list

    def get_spec_for_field(self, field):
        return (
            field.field_id,
            get_backend_type("thrift", field.field_type.type_id),
            field.field_name,
            self.get_spec_type_parameter(field.field_type),
            field.default,)

class ThriftTupleAdapter(object):
    def __init__(self, field_definition, field_value):
        self.field_definition = field_definition
        self.field_value = field_value
        # This is probably very inefficient,
        # maybe we can optimize it someday
        self.tuple_struct_class = self.get_tuple_struct_class()

    def get_tuple_struct_name(self):
        return "%s_tuple" % (self.field_definition.field_name)

    def get_tuple_struct_class(self):
        field_dict = {}
        for ix in xrange(0, len(self.field_definition.field_type.type_parameters)):
            field_name = "tuple_%s" % ix
            type_parameter = self.field_definition.field_type.type_parameters[ix]
            field_dict[field_name] = Field(type_parameter)
        return type(
            self.get_tuple_struct_name(),
            (Unimodel,),
            field_dict)

    def write(self, protocol):
        obj = self.tuple_struct_class()
        for ix in xrange(0, len(self.field_value)):
            obj["tuple_%s" % ix] = self.field_value[ix]
        return obj.write(protocol)

    @classmethod
    def to_tuple(cls, tuple_struct_instance):
        elements = []
        for f in sorted(tuple_struct_instance.get_field_definitions(), key=lambda x: x.field_id):
            elements.append(tuple_struct_instance[f.field_name])
        return tuple(elements)

class ThriftValueConverter(object):
    
    def to_internal(self, field_definition, field_value):
        if isinstance(field_definition.field_type, types.UTF8):
            # TODO: not python3 friendly
            if type(field_value) == unicode:
                pass
            else:
                field_value = field_value.decode('utf-8')
        if isinstance(field_definition.field_type, types.BigInt):
            if field_value is None:
                field_value = 0
            field_value = long(field_value)
        if isinstance(field_definition.field_type, types.JSONData):
            field_value = json.loads(field_value)
        if isinstance(field_definition.field_type, types.Tuple):
            field_value = ThriftTupleAdapter.to_tuple(field_value)
        return field_value

    def from_internal(self, field_definition, field_value):
        if isinstance(field_definition.field_type, types.UTF8):
            field_value = field_value.encode('utf-8')
        if isinstance(field_definition.field_type, types.BigInt):
            field_value = None if field_value is None else str(field_value)
        if isinstance(field_definition.field_type, types.JSONData):
            field_value = json.dumps(field_value)
        if isinstance(field_definition.field_type, types.Tuple):
            field_value = ThriftTupleAdapter(field_definition, field_value)
        return field_value


def make_protocol_factory(protocol_class):

    conv = ThriftValueConverter()

    @contextmanager
    def converter(obj):
        old_value_converter = getattr(obj, '_value_converter', None)
        try:
            obj._set_value_converter(conv)
            yield
        #except Exception, e:
        #    import pdb;pdb.set_trace()
        finally:
            obj._set_value_converter(old_value_converter)
    
    # invoke converter when reading / writing fields
    class Protocol(protocol_class):

        def writeStruct(self, obj, thrift_spec):
            with converter(obj):
                return protocol_class.writeStruct(self, obj, thrift_spec)

        def readStruct(self, obj, thrift_spec):
            with converter(obj):
                return protocol_class.readStruct(self, obj, thrift_spec)

    class ProtocolFactory(object):
      def getProtocol(self, trans):
          return Protocol(trans)

    return ProtocolFactory()

class ThriftProtocol(object):

    factories = [
        ('binary', make_protocol_factory(TBinaryProtocol)),
        ('json', make_protocol_factory(TJSONProtocol)),
        ('compact', make_protocol_factory(TCompactProtocol))
    ]

    @classmethod
    def iter(cls):
        current = 0
        while current < len(cls.factories):
            yield cls.factories[current]
            current += 1

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
        if isinstance(protocol_name_or_id, int):
            protocol = self.lookup_by_id(protocol_name_or_id)
        else:
            protocol = self.lookup_by_name(protocol_name_or_id)
        self.id, self.name, self.factory = protocol

default_protocol_factory = ThriftProtocol('binary').factory


class ThriftSerializer(Serializer):

    def __init__(
            self,
            protocol_factory=default_protocol_factory,
            **kwargs):
        super(ThriftSerializer, self).__init__(**kwargs)
        self.protocol_factory = protocol_factory
        self.spec_factory = ThriftSpecFactory(self.model_registry)

    def serialize(self, obj):
        transport = TTransport.TMemoryBuffer()
        protocol = self.protocol_factory.getProtocol(transport)
        setattr(protocol, "serializer", self)
        self.write_to_stream(obj, protocol)
        transport._buffer.seek(0)
        return transport._buffer.getvalue()

    def deserialize(self, cls, stream):
        obj = self.model_registry.lookup(cls)()
        transport = TTransport.TMemoryBuffer()
        transport._buffer.write(stream)
        transport._buffer.seek(0)
        protocol = self.protocol_factory.getProtocol(transport)
        setattr(protocol, "serializer", self)
        self.read_from_stream(obj, protocol)
        return obj

    def write_to_stream(self, obj, protocol):
        return protocol.writeStruct(
            obj,
            self.spec_factory.get_spec_for_struct(
                obj.__class__))

    def read_from_stream(self, obj, protocol):
        protocol.readStruct(
            obj,
            self.spec_factory.get_spec_for_struct(
                obj.__class__))
