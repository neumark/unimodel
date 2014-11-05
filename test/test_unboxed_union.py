from unittest import TestCase
from thrift.Thrift import TType
from unimodel.model import Unimodel, Field
from unimodel import types
from unimodel.backends.thrift.serializer import ThriftSerializer, ThriftProtocol, ThriftSpecFactory

class G(Unimodel):
    g1 = Field(types.Int)
    g2 = Field(types.Int)

class U(Unimodel):
    # this will be an unboxed union
    f1 = Field(types.UTF8)
    f2 = Field(types.Int)
    f3 = Field(types.Struct(G))

class ExampleClass(Unimodel):
    u = Field(types.UTF8)
    f = Field(types.Struct(U))

# This class currently doesn't work and will not work
# until the JSON wireformat works once again
class UnboxedUnionTestCase(object): #TestCase):

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
            s = py_data.serialize(ThriftProtocol('json').factory)
            parsed_serialized_data = json.loads(s)
            self.assertEqual(flatten(parsed_serialized_data), flatten(json_data))

    def test_deserialization(self):
        for py_data, json_data in self.testdata:
            read = ExampleClass.deserialize(json.dumps(json_data), ThriftProtocol('json').factory)
            self.assertEqual(flatten(py_data), flatten(read))

    def test_too_many_fields_set(self):
        d = ExampleClass(u=U(f2=1,f1="a"))
        self.assertRaises(SerializationException , lambda: d.serialize(ThriftProtocol('json').factory))

    def test_read_value_doesnt_match(self):
        """ Only values of f which are of the expected types can be read """
        e = None
        try:
            # Note: f can be a struct, int or string, a list will not parse.
            deserialize(ExampleClass, '{"f":[]}', ThriftProtocol('json').factory)
        except ReadValidationException, e:
            pass
        self.assertNotEquals(e, None)
        self.assertEquals(sorted(e.data.keys()), ['f1', 'f2', 'f3'])

