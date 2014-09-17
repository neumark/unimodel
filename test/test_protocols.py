from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from thriftmodel.model import serialize, deserialize
from test.fixtures import NodeData, TreeNode, data
from test.helpers import flatten
import pprint

class ProtocolTestCase(TestCase):

    def test_serialize(self):
        for protocol_name, protocol_factory in Protocol.iter():
            pre_flattened = flatten(data)
            s = serialize(data)
            d = TreeNode.deserialize(s)
            self.assertEquals(d.__class__, TreeNode)
            post_flattened = flatten(d)
            self.assertEquals(pre_flattened, post_flattened, "%s serializes as expected" % protocol_name)
