from unittest import TestCase
from thrift.Thrift import TType
from unimodel.backends.json.serializer import JSONSerializer
from test.helpers import flatten
from test.fixtures import TreeNode, data
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json

class JSONSerializerTestCase(TestCase):

    def test_unicode_and_binary(self):
        """ serialize unicode and binary data """
        class ExampleClass(Unimodel):
            u = Field(UTF8, required=True)
            s = Field(Binary)

        test_string1 = unichr(40960)
        test_string2 = b"alma"
        data = ExampleClass(u=test_string1, s=test_string2)
        serializer = JSONSerializer()
        s = serializer.serialize(data)
        json_data = json.loads(s)
        d = serializer.deserialize(ExampleClass, s)
        self.assertEquals(d.s, data.s)
        self.assertEquals(d.u, data.u)
        self.assertEquals(type(d.u), unicode)
        self.assertNotEquals(d.s, json_data['s'])

    def test_json_serialize(self):
        """ serialize a complex recursive datatype into JSON """
        pre_flattened = flatten(data)
        serializer = JSONSerializer()
        s = serializer.serialize(data)
        d = serializer.deserialize(TreeNode, s)
        self.assertEquals(d.__class__, TreeNode)
        post_flattened = flatten(d)

    def test_read_validation(self):
        class A(Unimodel):
            u = Field(List(Int))
        json_str = '{"u": ["a", "b", "c"]}'
        serializer = JSONSerializer()
        d = serializer.deserialize(A, json_str)

