from thrift.Thrift import TType
from thrift.protocol import TBinaryProtocol, TCompactProtocol, TJSONProtocol
from thriftmodel import TFlexibleJSONProtocol
from thriftmodel.util import replace_tuple_element

def utf8fix(protocol_factory):
    original_getProtocol = protocol_factory.getProtocol
    def patched_getProtocol(trans):
        protocol = original_getProtocol(trans)
        # patch _TTYPE_HANDLERS to support unicode if necessary
        if hasattr(protocol, '_TTYPE_HANDLERS'):
            utf8_field_def = protocol._TTYPE_HANDLERS[TType.UTF8]
            if utf8_field_def[0:2] == (None, None):
                def readUTF8String():
                    return protocol.readString().decode('utf-8')
                def writeUTF8String(unicode_str):
                    return protocol.writeString(unicode_str.encode('utf-8'))
                # register [write|read]UTF8String as a call to the original
                # [write|read]String + unicode encoding and decoding
                protocol._TTYPE_HANDLERS = replace_tuple_element(
                    protocol._TTYPE_HANDLERS,
                    TType.UTF8,
                    ('readUTF8String', 'writeUTF8String', False))
                protocol.readUTF8String = readUTF8String
                protocol.writeUTF8String = writeUTF8String
        return protocol
    protocol_factory.getProtocol = patched_getProtocol
    return protocol_factory

class Protocol(object):

    factories = [
        ('binary', utf8fix(TBinaryProtocol.TBinaryProtocolFactory())),
        ('verbose_json', utf8fix(TJSONProtocol.TJSONProtocolFactory())),
        ('json', utf8fix(TFlexibleJSONProtocol.TFlexibleJSONProtocolFactory())),
        ('compact', utf8fix(TCompactProtocol.TCompactProtocolFactory()))
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
