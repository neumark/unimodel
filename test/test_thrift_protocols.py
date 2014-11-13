from unittest import TestCase
from test.fixtures import NodeData, TreeNode, AllTypes, tree_data, all_types_data
from test.helpers import flatten
from unimodel.backends.thrift.serializer import ThriftSerializer, ThriftProtocol


class ThriftProtocolTestCase(TestCase):

    def test_thrift_serialize_tree_data(self):
        for protocol_name, protocol_factory in ThriftProtocol.iter():
            serializer = ThriftSerializer(protocol_factory=protocol_factory)
            s = serializer.serialize(tree_data)
            d = serializer.deserialize(TreeNode, s)
            self.assertEquals(d.__class__, TreeNode)
            self.assertEquals(
                tree_data,
                d,
                "%s serializes as expected" %
                protocol_name)

    def test_thrift_serialize_all_types_data(self):
        for protocol_name, protocol_factory in ThriftProtocol.iter():
            serializer = ThriftSerializer(protocol_factory=protocol_factory)
            for ix in xrange(0, len(all_types_data)):
                s = serializer.serialize(all_types_data[ix])
                d = serializer.deserialize(AllTypes, s)
                self.assertEquals(d.__class__, AllTypes)
                self.assertEquals(
                    all_types_data[ix],
                    d,
                    "%s serializes all_fields[%s]" %
                    (protocol_name, ix))
