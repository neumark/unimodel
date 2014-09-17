from thrift.protocol import TBinaryProtocol, TCompactProtocol, TJSONProtocol
from thriftmodel import TFlexibleJSONProtocol

class Protocol(object):

    factories = [
        ('binary', TBinaryProtocol.TBinaryProtocolFactory()),
        ('verbose_json', TJSONProtocol.TJSONProtocolFactory()),
        ('json', TFlexibleJSONProtocol.TFlexibleJSONProtocolFactory()),
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

default_protocol_factory=Protocol('binary').factory
