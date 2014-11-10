from unittest import TestCase
from unimodel.model import Unimodel, Field, FieldFactory
from unimodel import types
from unimodel.backends.thrift.serializer import ThriftSerializer, ThriftProtocol
from unimodel.backends.json.serializer import JSONSerializer
from unimodel.backends.json.schema import JSONSchemaWriter


class A(Unimodel):
    f = Field(types.Tuple(types.Int, types.UTF8, types.Int))


class TupleTestCase(TestCase):

    def notest_thrift_serialize(self):
        data = A(f=(1, "asdf", 2))
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
