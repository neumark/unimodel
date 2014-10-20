from unittest import TestCase
from thriftmodel.protocol import Protocol
from thriftmodel.model import (serialize, deserialize,
        ThriftField, ThriftModel, IntField, ListField,
        MapField, StringField, StructField, serialize, deserialize)

FIELD_NAME1 = 'long-hypenated-name'
FIELD_NAME2 = 'a:""f'

class FieldNameTestClass(ThriftModel):
    shortname = StringField(thrift_field_name=FIELD_NAME1)
    f = IntField(thrift_field_name=FIELD_NAME2)


class ProtocolTestCase(TestCase):

    def test_constructor_args(self):
        VALUE1 = "asdf"
        VALUE2 = 2
        a = FieldNameTestClass(VALUE1, VALUE2)
        self.assertEquals(a.shortname, VALUE1)
        self.assertEquals(a.f, VALUE2)

    def test_constructor_args(self):
        VALUE1 = "asdf"
        VALUE2 = 2
        a = FieldNameTestClass(f=VALUE2, shortname=VALUE1)
        self.assertEquals(a.shortname, VALUE1)
        self.assertEquals(a.f, VALUE2)

    def test_bracket_access(self):
        VALUE1 = "asdf"
        VALUE2 = 2
        a = FieldNameTestClass(f=VALUE2, shortname=VALUE1)
        self.assertEquals(a[FIELD_NAME1], VALUE1)
        self.assertEquals(a[FIELD_NAME2], VALUE2)
        a[FIELD_NAME2] = 42
        self.assertEquals(a.f, 42)

    def test_only_iterate_set_values(self):
        a = FieldNameTestClass(shortname="a")
        self.assertEquals([f for f in a], [FIELD_NAME1])
