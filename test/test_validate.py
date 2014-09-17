from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from thriftmodel.model import serialize, deserialize
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, UTF8Field, StructField, serialize, deserialize)

class ValidationTestClass(ThriftModel):
    important_string = UTF8Field(required=True)

class ValidationTestCase(TestCase):

    def test_validate(self):
        data = ValidationTestClass()
        s = serialize(data, Protocol('json').factory)
        self.assertRaises(ReadValidationException,
                lambda: ValidationTestClass.deserialize(s, Protocol('json').factory))
