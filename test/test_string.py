from unittest import TestCase
import json
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from thriftmodel.model import serialize, deserialize
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize)

class ExampleClass(ThriftModel):
    u = UTF8Field(required=True)
    s = StringField()

class StringTestCase(TestCase):

    PROTOCOL_OPTS = {'base64_encode_string': True}

    def test_unicode_and_binary(self):
        test_string1 = unichr(40960)
        test_string2 = "alma"
        data = ExampleClass(u=test_string1, s=test_string2)
        s = data.serialize(Protocol('json').factory, self.PROTOCOL_OPTS)
        json_data = json.loads(s)
        d = ExampleClass.deserialize(s, Protocol('json').factory, self.PROTOCOL_OPTS)
        self.assertEquals(d.s, data.s)
        self.assertEquals(d.u, data.u)
        self.assertEquals(type(d.u), unicode)
        self.assertNotEquals(d.s, json_data['s'])

