from unittest import TestCase
from thrift.Thrift import TType
from unimodel.backends.json.serializer import JSONSerializer
from test.helpers import flatten
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json

class ExampleClass(Unimodel):
    u = Field(UTF8, required=True)
    s = Field(Binary)

class StringTestCase(TestCase):

    def nonworking_test_unicode_and_binary(self):
        test_string1 = unichr(40960)
        test_string2 = b"alma"
        data = ExampleClass(u=test_string1, s=test_string2)
        serializer = JSONSerializer()
        s = serializer.serialize(data)
        json_data = json.loads(s)
        d = serializer.deserialize(TreeNode, s)
        self.assertEquals(d.s, data.s)
        self.assertEquals(d.u, data.u)
        self.assertEquals(type(d.u), unicode)
        self.assertNotEquals(d.s, json_data['s'])

