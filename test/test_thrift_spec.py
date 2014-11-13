from unittest import TestCase
from thrift.Thrift import TType
from unimodel.model import Unimodel, Field
from unimodel import types
from unimodel.backends.thrift.serializer import ThriftSpecFactory
from unimodel.util import get_backend_type


class ThriftSpecTestCase(TestCase):

    """

    struct A {
        1: i64 a,
        2: BannedClient c,
        3: i64 d=6,
        4: list<string> e,
        5: list<BannedClient> f
        6: map<i64, string> g
        7: list<map<i64, list<BannedClient>>> h
    }

     compiles to:

      thrift_spec = (
        None, # 0
        (1, TType.I64, 'a', None, None, ), # 1
        (2, TType.STRUCT, 'c', (BannedClient, BannedClient.thrift_spec), None, ), # 2
        (3, TType.I64, 'd', None, 6, ), # 3
        (4, TType.LIST, 'e', (TType.STRING,None), None, ), # 4
        (5, TType.LIST, 'f', (TType.STRUCT,(BannedClient, BannedClient.thrift_spec)), None, ), # 5
        (6, TType.MAP, 'g', (TType.I64,None,TType.STRING,None), None, ), # 6
        (7, TType.LIST, 'h', (TType.MAP,(TType.I64,None,TType.LIST,(TType.STRUCT,(BannedClient, BannedClient.thrift_spec)))), None, ), # 7
      )
    """

    def __init__(self, *args, **kwargs):
        super(ThriftSpecTestCase, self).__init__(*args, **kwargs)
        self.spec_factory = ThriftSpecFactory()

    def get_field_spec(self, field):
        return self.spec_factory.get_spec_for_field(field)

    def test_simple_field(self):
        FIELD_TYPE = types.Int()
        FIELD_NAME = "apple"
        FIELD_ID = 1
        DEFAULT = "1"
        field = Field(
            field_type=FIELD_TYPE,
            field_name=FIELD_NAME,
            field_id=FIELD_ID,
            default=DEFAULT)
        self.assertEquals(
            self.get_field_spec(field),
            (FIELD_ID,
             get_backend_type("thrift", field.field_type.type_id),
             FIELD_NAME,
             None,
             DEFAULT))

    def test_list_field(self):
        field = Field(types.List(types.Int))
        field_spec = self.get_field_spec(field)
        self.assertEquals(
            (-1, TType.LIST, None, [TType.I64, None], None),
            field_spec)

    def test_map_field(self):
        field = Field(types.Map(types.Int, types.UTF8))
        self.assertEquals(self.get_field_spec(
            field), (-1, TType.MAP, None, [TType.I64, None, TType.STRING, None], None))

    def test_struct_field(self):
        field = Field(types.Int)

        class F(Unimodel):
            f = field
        struct_spec = self.spec_factory.get_spec_for_struct(F)
        self.assertEquals(struct_spec, [None, (1, 10, 'f', None, None)])
