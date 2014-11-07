from unittest import TestCase
from unimodel.backends.json.serializer import JSONSerializer, JSONValidationException
from unimodel.backends.json.type_data import JSONFieldData
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

    def test_enum_serialize(self):
        """ serialize a complex recursive datatype into JSON """
        class A(Unimodel):
            f = Field(Enum({1: "one", 2: "two"}))
        serializer = JSONSerializer()
        s = serializer.serialize(A(f=1))
        parsed_json = json.loads(s)
        self.assertEquals(parsed_json['f'], "one")
        d = serializer.deserialize(A, s)
        self.assertEquals(d.f, 1)
        exc = None
        try:
            serializer.serialize(A(f=33))
        except Exception, exc:
            pass
        self.assertTrue(isinstance(exc, ValueTypeException))

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
        exc = None
        try:
            d = serializer.deserialize(A, json_str)
        except Exception, exc:
            pass
        self.assertTrue(exc is not None)
        self.assertEquals(type(exc), JSONValidationException)
        self.assertEquals(exc.context.current_path(), "u[0]")
        self.assertEquals(exc.context.current_value(), "a")

    def test_unknown_fields(self):
        class A(Unimodel):
            u = Field(List(UTF8))
        json_str = '{"u": ["a", "b", "c"], "x": 1}'
        serializer = JSONSerializer()
        # by default, unknown fields are skipped
        d = serializer.deserialize(A, json_str)
        exc = None
        try:
            serializer = JSONSerializer(skip_unknown_fields=False)
            d = serializer.deserialize(A, json_str)
        except Exception, exc:
            pass
        self.assertTrue(exc is not None)
        self.assertEquals(type(exc), JSONValidationException)
        self.assertEquals(exc.context.current_path(), "")
        self.assertTrue("unknown fields" in str(exc))

    def test_map_key_types(self):
        class A(Unimodel):
            a = Field(Map(UTF8, Int))
            b = Field(Map(Binary, Int))
            c = Field(Map(Int8, Int))
            d = Field(Map(Int, Int))
            e = Field(Map(Enum({1: "one", 2: "two"}), Int))

        data = A(
                a = {"a": 1},
                b = {bin(173): 1},
                c = {1: 1},
                d = {2**40: 1},
                e = {2: 1})

        serializer = JSONSerializer()
        s = serializer.serialize(data)
        read_data = serializer.deserialize(A, s)
        self.assertEquals(data, read_data)

        class B(Unimodel):
            a = Field(Map(Double, Int))

        exc = None
        try:
            print serializer.serialize(B(a={2.333: 1}))
        except Exception, exc:
            pass

    def test_custom_field_names(self):
        NAME = "/-/"
        class A(Unimodel):
            a = Field(Map(UTF8, Int), metadata=Metadata(backend_data={'json': JSONFieldData(property_name=NAME)}))

        serializer = JSONSerializer()
        data = A(a={"a":1})
        s = serializer.serialize(data)
        parsed_json = json.loads(s)
        self.assertTrue(NAME in parsed_json)
        self.assertEquals(data, serializer.deserialize(A, s))
 
    def test_unboxed_struct(self):
        class Unboxed(Unimodel):
            a = Field(Int)
            b = Field(Int)

        class Parent(Unimodel):
            a = Field(
                    Struct(Unboxed),
                    metadata=Metadata(
                        backend_data={'json': JSONFieldData(is_unboxed=True)}))
            c = Field(Int)

        serializer = JSONSerializer()
        data = Parent(a=Unboxed(a=1,b=2),c=3)
        s = serializer.serialize(data)
        parsed_json = json.loads(s)
        self.assertEquals(sorted(parsed_json.keys()), ["a", "b", "c"])
        self.assertEquals(data, serializer.deserialize(Parent, s))
