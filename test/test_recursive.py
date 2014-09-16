from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.model import (
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, StringField, StructField, serialize, deserialize)


class NodeData(ThriftModel):
    name = StringField()
    age = IntField()
    skills = MapField(StringField(), IntField())

class TreeNode(RecursiveThriftModel):
    pass

TreeNode.make_thrift_spec({
        'children': ListField(TreeNode),
        'data': StructField(NodeData)})


class RecursiveTypeTestCase(TestCase):

    def test_recursive_spec(self):
        """
        (-1,
         12,
         'TreeNode',
         (<class 'test.test_recursive.TreeNode'>,
          [None,
           (1,
            15,
            'children',
            (12,
             (<class 'test.test_recursive.TreeNode'>,
              <Recursion on list with id=4507404408>)),
            None),
           (2,
            12,
            'data',
            (<class 'test.test_recursive.NodeData'>,
             (None,
              (1, 11, 'name', None, None),
              (2, 10, 'age', None, None),
              (3, 13, 'skills', (11, None, 10, None), None))),
            None)]),
         None)
        """
        thrift_spec = TreeNode.to_tuple()
        self.assertEquals(thrift_spec[1], TType.STRUCT)
        self.assertEquals(thrift_spec[2], TreeNode.__name__)
        self.assertEquals(thrift_spec[3][0], TreeNode)
        self.assertEquals(thrift_spec[3][1][1][1], TType.LIST)
        self.assertEquals(thrift_spec[3][1][1][2], 'children')
        self.assertEquals(thrift_spec[3][1][2][1], TType.STRUCT)
        self.assertEquals(thrift_spec[3][1][2][2], 'data')
        # test recursion
        self.assertEquals(thrift_spec[3][1][1][3][1][1], thrift_spec[3][1])

    def test_serialize(self):
        data = TreeNode(
                children=[
                    TreeNode(
                            children=[TreeNode(data=NodeData(name="ulrik", age=9))],
                            data=NodeData(
                                name="josef",
                                age=33,
                                skills={
                                    "guitar": 5,
                                    "swimming": 10}),
                        ),
                    TreeNode(
                        data=NodeData(name="julia", age=27)),
                    TreeNode(
                            children=[
                                TreeNode(
                                    data=NodeData(name="hans", age=91),
                                    children=[NodeData(name="A")])
                            ],
                            data=NodeData(name="julio", age=67)
                        )
                    ]
               )

        s = serialize(data)
        d = TreeNode.deserialize(s)
        self.assertEquals(d.__class__, TreeNode)
        self.assertEquals(sorted([c.data.name for c in d.children]), ["josef", "julia", "julio"])

class NonRecursiveTypeTestCase(TestCase):
    def test_nonrecursive_spec_is_tuple(self):
        """ Nonrecursive thrift_specs are tuples.
            Important because the accelerated binary protocol doesn't like
            lists in thrift specs. """
        self.assertEquals(type(NodeData.to_tuple()), tuple)
        [self.assertNotEquals(type(t), list) for t in NodeData.to_tuple()]

    def test_accelerated_binary(self):
        from thrift.protocol.TBinaryProtocol import TBinaryProtocolAcceleratedFactory
        factory = TBinaryProtocolAcceleratedFactory()
        data = NodeData(age=7, name="asdf")
        s = serialize(data, factory)
        d = NodeData.deserialize(s, factory)
        self.assertEquals(d.__class__, NodeData)

