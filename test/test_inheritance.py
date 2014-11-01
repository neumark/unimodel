from unittest import TestCase
from thrift.Thrift import TType
from thriftmodel.protocol import Protocol
from test.helpers import flatten
from thriftmodel.TFlexibleJSONProtocol import ReadValidationException
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, IntField, ListField,
        MapField, StringField, UTF8Field, StructField, serialize, deserialize,
        ValidationException, BoolField, FieldMerger, ThriftFieldMergeException)

class FieldMergerTestCase(TestCase):

    def test_basic_merge(self):
        field1 = IntField(thrift_field_name='a', field_id=2)
        field2 = IntField(thrift_field_name='b', field_id=1)
        fm = FieldMerger(
            [('a', field1)],
            [('b', field2)])
        result = sorted(fm.merge(), key=lambda x:x[0])
        # basic merge scenario: both list have non-conflicting fields
        self.assertEquals(result, [('a', field1), ('b', field2)])

        # test_empty_to_merge_list
        fm = FieldMerger([('a', field1), ('b', field2)], [])
        result = sorted(fm.merge(), key=lambda x:x[0])
        self.assertEquals(result, [('a', field1), ('b', field2)])

        # test empty original list
        fm = FieldMerger([], [('a', field1), ('b', field2)])
        result = sorted(fm.merge(), key=lambda x:x[0])
        self.assertEquals(result, [('a', field1), ('b', field2)])

    def test_field_name_mandatory(self):
        """ the thrift_field_name attribute is mandatory.
        """
        field1 = IntField(field_id=2, thrift_field_name='a')
        field2 = IntField(field_id=1)
        def f():
            fm = FieldMerger(
                [('a', field1)],
                [('b', field2)])
        self.assertRaises(ThriftFieldMergeException, lambda: f())

        field1 = IntField(field_id=2)
        field2 = IntField(field_id=1)
        def f():
            fm = FieldMerger(
                [('a', field1)],
                [('b', field2)])
        self.assertRaises(ThriftFieldMergeException, lambda: f())

    def test_field_id_mandatory(self):
        """ Field id is mandatory in the original field list.
        Optional in to_merge fields."""
        field1 = IntField(field_id=1, thrift_field_name='a')
        field2 = IntField(thrift_field_name='b')
        fm = FieldMerger(
            [('a', field1)],
            [('b', field2)])
        result = sorted(fm.merge(), key=lambda x:x[0])
        self.assertEquals(result, [('a', field1), ('b', field2)])


        field1 = IntField(thrift_field_name='a')
        field2 = IntField(field_id=1, thrift_field_name='b')
        def fun():
            fm = FieldMerger(
                [('b', field1)],
                [('a', field2)])
            fm.merge()
        self.assertRaises(ThriftFieldMergeException, lambda: fun())


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


