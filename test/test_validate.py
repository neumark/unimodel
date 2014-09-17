from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from thriftmodel.model import serialize, deserialize
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize)

class ValidationTestClass(ThriftModel):
    important_string = StringField(required=True)

class ValidationTestCase(TestCase):

    def test_missing_required(self):
        data = ValidationTestClass()
        s = serialize(data, Protocol('json').factory)
        # a missing required field causes an exception
        self.assertRaises(ReadValidationException,
            lambda: ValidationTestClass.deserialize(s, Protocol('json').factory))
        data.important_string = "asdf"
        s = serialize(data, Protocol('json').factory)
        ValidationTestClass.deserialize(s, Protocol('json').factory)
        # deleting the field again causes the exception
        del data['important_string']
        s = serialize(data, Protocol('json').factory)
        self.assertRaises(ReadValidationException,
            lambda: ValidationTestClass.deserialize(s, Protocol('json').factory))

