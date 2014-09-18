from unittest import TestCase
import json
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from thriftmodel.model import serialize, deserialize
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException, SerializationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, UnboxedUnion,
        IntField, ListField, MapField, StringField, UTF8Field,
        StructField, serialize, deserialize)

class G(ThriftModel):
    g1 = IntField()
    g2 = IntField()

class U(ThriftModel, UnboxedUnion):
    f1 = UTF8Field()
    f2 = IntField()
    f3 = StructField(G)

class ExampleClass(ThriftModel):
    u = UTF8Field()
    f = StructField(U)


class UnboxedUnionTestCase(TestCase):

    v1 = "asdf"
    v2 = 12
    v3 = (18, 213)

    u1 = U(f1=v1)
    u2 = U(f2=12)
    u3 = U(f3=G(
        g1=v3[0],
        g2=v3[1]))

    testdata = [
            (ExampleClass(u = v1, f = u1), {'u': v1, "f":v1}),
            (ExampleClass(u = v1, f = u2), {'u': v1, "f":v2}),
            (ExampleClass(u = v1, f = u3), {'u': v1, "f":{"g1":v3[0], "g2":v3[1]}}),
            (ExampleClass(u = v1), {'u': v1})]

    def test_serialization(self):
        for py_data, json_data in self.testdata:
            s = py_data.serialize(Protocol('json').factory)
            parsed_serialized_data = json.loads(s)
            self.assertEqual(flatten(parsed_serialized_data), flatten(json_data))

    def test_deserialization(self):
        for py_data, json_data in self.testdata:
            read = ExampleClass.deserialize(json.dumps(json_data), Protocol('json').factory)
            self.assertEqual(flatten(py_data), flatten(read))

    def test_too_many_fields_set(self):
        d = ExampleClass(u=U(f2=1,f1="a"))
        self.assertRaises(SerializationException , lambda: d.serialize(Protocol('json').factory))

    def test_read_value_doesnt_match(self):
        """ Only values of f which are of the expected types can be read """
        e = None
        try:
            # Note: f can be a struct, int or string, a list will not parse.
            deserialize(ExampleClass, '{"f":[]}', Protocol('json').factory)
        except ReadValidationException, e:
            pass
        self.assertNotEquals(e, None)
        self.assertEquals(sorted(e.data.keys()), ['f1', 'f2', 'f3'])

