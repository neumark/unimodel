from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize,
        ValidationException, BoolField)

class ModelInheritanceTestCase(TestCase):

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


