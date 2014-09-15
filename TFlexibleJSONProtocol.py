from thrift.protocol.TProtocol import TType, TProtocolBase, TProtocolException
from thrift.protocol.TJSONProtocol import TSimpleJSONProtocol
import base64
import json
import math

__all__ = ['TFlexibleJSONProtocol',
           'TFlexibleJSONProtocolFactory']

VERSION = 1

class TFlexibleJSONProtocol(TSimpleJSONProtocol):
    def readMessageBegin(self):
        self.data = json.loads(self.protocol.trans.readAll())
        import pdb;pdb.set_trace()
    
    def readMessageEnd(self):
        raise NotImplementedError()
    
    def readStructBegin(self):
        raise NotImplementedError()
    
    def readStructEnd(self):
        raise NotImplementedError()
 
class TFlexibleJSONProtocolFactory(object):

    def getProtocol(self, trans):
        return TFlexibleJSONProtocol(trans)
