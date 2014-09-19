from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, RecursiveThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize,
        ValidationException)

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

    def test_custom_field_validator(self):
        class EvenValidator(object):
            def validate(self, value):
                if value % 2 > 0:
                    raise ValidationException("%s is not odd" % value)

        class G(ThriftModel):
            f = IntField(validators=[EvenValidator()])

        obj = G(f=1)
        self.assertRaises(ValidationException, lambda: obj.validate())
        obj.f = 2
        # this doesn't raise
        obj.validate()

    def test_custom_model_validator(self):
        class EvenValidator(object):
            def validate(self, g):
                if g.f % 2 > 0:
                    raise ValidationException("f is not odd (f == %s)" % g.f)

        class G(ThriftModel):
            f = IntField()
            validators=[EvenValidator()]

        obj = G(f=1)
        self.assertRaises(ValidationException, lambda: obj.validate())
        obj.f = 2
        # this doesn't raise
        obj.validate()
