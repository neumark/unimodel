from unittest import TestCase
from test.fixtures import NodeData, TreeNode, data
from test.helpers import flatten
from unimodel.wireformat_thrift.serialization import ThriftSerializer, ThriftProtocol

class ProtocolTestCase(TestCase):

    def test_serialize(self):
        pre_flattened = flatten(data)
        for protocol_name, protocol_factory in ThriftProtocol.iter():
            serializer = ThriftSerializer(protocol_factory=protocol_factory)
            s = serializer.serialize(data)
            d = serializer.deserialize(TreeNode, s)
            self.assertEquals(d.__class__, TreeNode)
            post_flattened = flatten(d)
            self.assertEquals(pre_flattened, post_flattened, "%s serializes as expected" % protocol_name)
