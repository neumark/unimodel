from thrift.protocol import TBinaryProtocol, TCompactProtocol, TJSONProtocol
from thrift.transport import TTransport
from thrift.protocol.TBase import TBase
from thriftmodel.model import ModelRegistry
from thriftmodel.wireformat_thrift.type_info import ThriftSpecFactory

try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None

class ThriftProtocol(object):

    factories = [
        ('binary', TBinaryProtocol.TBinaryProtocolFactory()),
        ('fastbinary', TBinaryProtocol.TBinaryProtocolAcceleratedFactory()),
        ('json', TJSONProtocol.TJSONProtocolFactory()),
        ('simple_json', TJSONProtocol.TSimpleJSONProtocolFactory()),
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
        if type(protocol_name_or_id) == int:
            protocol = self.lookup_by_id(protocol_name_or_id)
        else:
            protocol = self.lookup_by_name(protocol_name_or_id)
        self.id, self.name, self.factory =  protocol

default_protocol_factory=ThriftProtocol('binary').factory

class ThriftSerializer(object):

    def __init__(self,
            protocol_factory=default_protocol_factory,
            model_registry=None):
        self.protocol_factory = protocol_factory
        self.model_registry = model_registry or ModelRegistry()
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
        return protocol.writeStruct(obj, self.spec_factory.get_spec_for_struct(obj.__class__))

    def read_from_stream(self, obj, protocol):
        protocol.readStruct(obj, self.spec_factory.get_spec_for_struct(obj.__class__))
