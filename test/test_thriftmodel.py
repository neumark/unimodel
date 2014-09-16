from unittest import TestCase
from thriftmodel import ThriftField

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


    def test_simple_field(self):
        FIELD_TYPE=200
        FIELD_NAME="apple"
        FIELD_ID=1
        DEFAULT="1"
        field = ThriftField(
            FIELD_TYPE,
            thrift_field_name=FIELD_NAME,
            field_id=FIELD_ID,
            default=DEFAULT)
        self.assertEquals(field.to_tuple(), 
                (FIELD_ID, FIELD_TYPE, FIELD_NAME, None, DEFAULT))

    def test_list_field(self):
        field = ThriftField(
            FIELD_TYPE,
            thrift_field_name=FIELD_NAME,
            field_id=FIELD_ID,
            default=DEFAULT)
        self.assertEquals(field.to_tuple(), 
                (FIELD_ID, FIELD_TYPE, FIELD_NAME, None, DEFAULT))
