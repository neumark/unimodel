from unittest import TestCase
from thrift.Thrift import TType
from unimodel.backends.thrift.serializer import ThriftProtocol
from test.helpers import flatten
from unimodel.model import Unimodel, Field
from unimodel.metadata import Metadata
from unimodel.types import *

class ValidationTestClass(Unimodel):
    important_string = Field(UTF8, required=True)

class ValidationTestCase(TestCase):

    def nonworking_test_missing_required(self):
        data = ValidationTestClass()
        s = serialize(data, ThriftProtocol('json').factory)
        # a missing required field causes an exception
        self.assertRaises(ReadValidationException,
            lambda: ValidationTestClass.deserialize(s, ThriftProtocol('json').factory))
        data.important_string = "asdf"
        s = serialize(data, ThriftProtocol('json').factory)
        ValidationTestClass.deserialize(s, ThriftProtocol('json').factory)
        # deleting the field again causes the exception
        del data['important_string']
        s = serialize(data, ThriftProtocol('json').factory)
        self.assertRaises(ReadValidationException,
            lambda: ValidationTestClass.deserialize(s, ThriftProtocol('json').factory))

    def test_custom_field_validator(self):
        class EvenValidator(object):
            def validate(self, value):
                if value % 2 > 0:
                    raise ValidationException("%s is not odd" % value)

        class G(Unimodel):
            f = Field(Int(metadata=Metadata(validators=[EvenValidator()])))

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

        class G(Unimodel):
            f = Field(Int)
            metadata=Metadata(validators=[EvenValidator()])

        obj = G(f=1)
        self.assertRaises(ValidationException, lambda: obj.validate())
        obj.f = 2
        # this doesn't raise
        obj.validate()

    def test_type_parameter_validator(self):
        class ElementValidator(object):
            def validate(self, value):
                if value % 2 > 0:
                    raise ValidationException("f is not odd (f == %s)" % value)

        class ListValidator(object):
            def validate(self, l):
                if len(l) != 4:
                    raise ValidationException("list should have 4 elements")

        class G(Unimodel):
            f = Field(List(Int(metadata=Metadata(validators=[ElementValidator()]))))
 
        class F(Unimodel):
            f = Field(List(Int, metadata=Metadata(validators=[ListValidator()])))
 
        obj = G(f=[0,1])
        self.assertRaises(ValidationException, lambda: obj.validate())
        obj.f = [2,2]
        # this doesn't raise
        obj.validate()
        # this raises
        self.assertRaises(ValidationException, lambda: F(f=[1]).validate())
        F(f=[1,2,3,4]).validate()

    def test_validate_map(self):
        class KeyValidator(object):
            def validate(self, value):
                if value % 2 > 0:
                    raise ValidationException("f is not even (f == %s)" % value)

        class ValueValidator(object):
            def validate(self, l):
                if len(l) != 4:
                    raise ValidationException("list should have 4 elements")

        class F(Unimodel):
            f = Field(
                    Map(
                        Int(metadata=Metadata(validators=[KeyValidator()])),
                        List(UTF8, metadata=Metadata(validators=[ValueValidator()]))))
        # both key and value is OK
        F(f={2:["a", "b", "c", "d"]}).validate()
        # validation of key fails
        self.assertRaises(ValidationException, lambda: F(f={1: ["a", "b", "c", "d"]}).validate())
        # validation of value fails
        self.assertRaises(ValidationException, lambda: F(f={4: ["a", "b", "c"]}).validate())

    def test_validate_deeply_nested(self):
        class EvenValidator(object):
            def validate(self, value):
                if value % 2 > 0:
                    raise ValidationException("f is not even (f == %s)" % value)

        class F(Unimodel):
            f = Field(
                    List(
                        List(
                            List(
                                Map(
                                    UTF8(),
                                    List(
                                        List(
                                            Int(metadata=Metadata(validators=[EvenValidator()])))))))))

        # both key and value is OK
        F(f=[[[{"a":[[2]]}]]]).validate()
        # validation of int fails
        self.assertRaises(ValidationException, lambda: F(f=[[[{"a":[[3]]}]]]).validate())

    def test_validate_tree_path(self):
        # TODO: update the "validation path", which is just like the
        # json path so it's possible to tell where the failing value
        # was located.
        pass

