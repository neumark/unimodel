from unittest import TestCase
from test.fixtures import NodeData, TreeNode, data
from test.helpers import flatten
from unimodel.backends.thrift.serializer import ThriftSerializer, ThriftProtocol


class ThriftProtocolTestCase(TestCase):

    def test_thrift_serialize(self):
        pre_flattened = flatten(data)
        for protocol_name, protocol_factory in ThriftProtocol.iter():
            serializer = ThriftSerializer(protocol_factory=protocol_factory)
            s = serializer.serialize(data)
            d = serializer.deserialize(TreeNode, s)
            self.assertEquals(d.__class__, TreeNode)
            post_flattened = flatten(d)
            self.assertEquals(
                pre_flattened,
                post_flattened,
                "%s serializes as expected" %
                protocol_name)
