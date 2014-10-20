from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize,
        ValidationException, BoolField)

class ModelInheritanceTestCase(TestCase):

    def test_inherit_from_generated_python(self):
        from test.compiled.py.ttypes import SomeStruct
        class A(SomeStruct, ThriftModel):
            a = IntField()
        # A will have one more field than SomeStruct
        self.assertTrue(len(A.thrift_spec) == (len(SomeStruct.thrift_spec) + 1))
        # the last field of the thrift_spec will be a
        self.assertEquals(A.thrift_spec[-1][2], "a")


    def test_model_inheritance(self):
        class A(ThriftModel):
            a = IntField()
        class B(A):
            b = UTF8Field()
        class C(B):
            c = BoolField()

        class NoInherit(ThriftModel):
            a = IntField()
            b = UTF8Field()
            c = BoolField()

        self.assertEquals(C.thrift_spec, NoInherit.thrift_spec)

    def atest_field_override(self):
        # TODO: inheritance works based on the thrift_spec of the base class.
        # This means validators are lost and duplicate field names are used.
        # FIX THIS!
        class A(ThriftModel):
            a = IntField()
        class B(A):
            b = UTF8Field()
        class C(B):
            b = BoolField()

        class NoInherit(ThriftModel):
            a = IntField()
            b = BoolField()

        self.assertEquals(C.thrift_spec, NoInherit.thrift_spec)


