from unimodel.model import Unimodel, UnimodelUnion, Field, FieldFactory
from unimodel import types
import sys

class NodeData(Unimodel):
    name = Field(types.UTF8)
    age = Field(types.Int)
    skills = Field(types.Map(types.UTF8, types.Int))


class TreeNode(Unimodel):
    pass

field_factory = FieldFactory()
field_factory.add_fields(TreeNode, {
    'children': Field(types.List(types.Struct(TreeNode))),
    'data': Field(types.Struct(NodeData))})

class A(Unimodel):
    f = Field(types.Int)

class TestUnion(UnimodelUnion):
    f1 = Field(types.Struct(NodeData))
    f2 = Field(types.Struct(A))

class AllTypes(Unimodel):
    f_struct = Field(types.Struct(NodeData))
    f_union = Field(types.Struct(TestUnion))
    f_utf8 = Field(types.UTF8)
    f_binary = Field(types.Binary)
    f_int64 = Field(types.Int64)
    f_int32 = Field(types.Int32)
    f_int16 = Field(types.Int16)
    f_int8 = Field(types.Int8)
    f_double = Field(types.Double)
    f_enum = Field(types.Enum({1: "one", 2: "two", 3: "three"}))
    f_list = Field(types.List(types.Int))
    f_set = Field(types.Set(types.Int))
    f_map = Field(types.Map(types.UTF8, types.Int))
    f_tuple = Field(types.Tuple(types.UTF8, types.Int, types.Double))
    f_jsondata = Field(types.JSONData)
    f_bigint = Field(types.BigInt)

if sys.version < '3':
    import codecs
    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

tree_data = TreeNode(
    children=[
        TreeNode(
            children=[TreeNode(data=NodeData(name="ulrik", age=9))],
            data=NodeData(
                name="josef",
                age=33,
                skills={
                    "guitar": 5,
                    "swimming": 10}),
        ),
        TreeNode(
            data=NodeData(name="julia", age=27)),
        TreeNode(
            children=[
                TreeNode(
                    data=NodeData(name="hans", age=91),
                    children=[TreeNode(data=NodeData(name="A"))])
            ],
            data=NodeData(name="julio", age=67)
        )
    ]
)

all_types_data = []
all_types_data.append(AllTypes(
    f_struct = NodeData(name="hans", age=7),
    f_union = TestUnion(f1=NodeData(name="romero", age=27)),
    f_utf8 = u('\u00dcnic\u00f6de'),
    f_binary = bin(173),
    f_int64 = 2**40,
    f_int32 = 2**20,
    f_int16 = 2**10,
    f_int8 = 2**5,
    f_double = 3.14,
    f_enum = AllTypes.get_field_definition("f_enum").field_type.name_to_key("two"),
    f_list = [1,1,2,3,5],
    f_set = set([1,2,3,4]),
    f_map = {'a': 1, 'b': 2},
    f_tuple = ("a", 1, 2.5),
    f_jsondata = {"data": [1,2,3, {"b": []}]},
    f_bigint = 11111111111111111111111111111111111))


all_types_data.append(AllTypes(
    f_struct = NodeData(name="hans", age=7),
    f_union = TestUnion(f2=A(f=1)),
    f_utf8 = u('\u00dcnic\u00f6de'),
    f_binary = b'11211',
    f_int64 = 2**40,
    f_int32 = 2**20,
    f_int16 = 2**10,
    f_int8 = 2**5,
    f_double = 3.14,
    f_enum = 1,
    f_list = [1,1,2,3,5],
    f_set = set([1,2,3,4]),
    f_map = {'a': 1, 'b': 2},
    f_tuple = ("a", 1, 2.5),
    f_jsondata = {"data": [1,2,3, {"b": []}]}))
