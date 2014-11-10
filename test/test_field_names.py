from unittest import TestCase
from thrift.Thrift import TType
from unimodel.model import Unimodel, Field
from unimodel import types
from unimodel.backends.thrift.serializer import ThriftSpecFactory

FIELD_NAME1 = 'long-hypenated-name'
FIELD_NAME2 = 'a:""f'


class FieldNameTestClass(Unimodel):
    shortname = Field(types.UTF8, field_name=FIELD_NAME1)
    f = Field(types.Int, field_name=FIELD_NAME2)

# TODO: nonworking tests ATM, will fix when JSON serializer works


class ProtocolTestCase(object):  # TestCase):

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
