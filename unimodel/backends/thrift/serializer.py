from thrift.protocol import TBinaryProtocol, TCompactProtocol, TJSONProtocol
from thrift.transport import TTransport
from thrift.protocol.TBase import TBase
from unimodel.backends.base import Serializer
from unimodel.backends.thrift.type_data import TType
from unimodel.types import Tuple


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
            struct_class._fields_by_name.values(),
            key=lambda x: x.field_id)
        thrift_spec = [None]
        # save the spec to cache so recurisve data structures work.
        self._spec_cache[struct_class] = thrift_spec
        for f in field_list:
            thrift_spec.append(self.get_spec_for_field(f))
        return thrift_spec

    def get_tuple_type_parameter(self, field_type):
        # tuple_id =
        # (implementation_class, self.get_spec(implementation_class))
        return None

    def get_spec_type_parameter(self, field_type):
        """ Returns value 3 of the element
            in thrift_spec which defines this field. """
        # tuples are encoded as structs
        if isinstance(field_type, Tuple):
            return self.get_tuple_type_parameter(field_type)
        # structs are a special case
        if field_type.metadata.backend_data['thrift'].type_id == TType.STRUCT:
            interface_class = field_type.python_type
            implementation_class = self.model_registry.lookup(interface_class)
            return (implementation_class, self.get_spec(implementation_class))
        # If there are no type parameters, return None
        if not field_type.type_parameters:
            return None
        # lists, sets, maps
        spec_list = []
        for t in field_type.type_parameters:
            # for each type_parameter, first add the type's id
            spec_list.append(t.metadata.backend_data['thrift'].type_id)
            # then the type's parameters
            spec_list.append(self.get_spec_type_parameter(t))
        return spec_list

    def get_spec_for_field(self, field):
        return (
            field.field_id,
            field.field_type.metadata.backend_data['thrift'].type_id,
            field.field_name,
            self.get_spec_type_parameter(field.field_type),
            field.default,)


class ThriftProtocol(object):

    factories = [
        ('binary', TBinaryProtocol.TBinaryProtocolFactory()),
        ('json', TJSONProtocol.TJSONProtocolFactory()),
        ('compact', TCompactProtocol.TCompactProtocolFactory())
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
