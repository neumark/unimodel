from unittest import TestCase
from thrift.Thrift import TType
from unimodel.model import Unimodel, Field
from unimodel import types
from unimodel.backends.thrift.serializer import ThriftSerializer, ThriftProtocol, ThriftSpecFactory
from test.fixtures import NodeData, TreeNode, tree_data


class RecursiveTypeTestCase(TestCase):

    def test_recursive_spec(self):
        """ TreeNode thrift spec:
        [None,
         (1,
          15,
          'children',
          [12,
           (<class 'test.fixtures.TreeNode'>,
            <Recursion on list with id=4509634288>)],
          None),
         (2,
          12,
          'data',
          (<class 'test.fixtures.NodeData'>,
           [None,
            (1, 11, 'name', None, None),
            (2, 10, 'age', None, None),
            (3, 13, 'skills', [11, None, 10, None], None)]),
          None)]"""
        spec_factory = ThriftSpecFactory()
        thrift_spec = spec_factory.get_spec_for_struct(TreeNode)
        self.assertEquals(thrift_spec[1][3][0], TType.STRUCT)
        self.assertEquals(thrift_spec[1][3][1][0], TreeNode)
        self.assertEquals(thrift_spec[1][1], TType.LIST)
        self.assertEquals(thrift_spec[1][2], 'children')
        # test recursion
        self.assertEquals(thrift_spec[1][3][1][1][1][3][1][0], TreeNode)

    def test_serialize(self):
        serializer = ThriftSerializer()
        s = serializer.serialize(tree_data)
        d = serializer.deserialize(TreeNode, s)
        self.assertEquals(d.__class__, TreeNode)
        self.assertEquals(
            sorted([c.data.name for c in d.children]), ["josef", "julia", "julio"])
