from unimodel.model import Unimodel, Field, FieldFactory
from unimodel import types


class NodeData(Unimodel):
    name    = Field(types.UTF8)
    age     = Field(types.Int)
    skills  = Field(types.Map(types.UTF8, types.Int))

class TreeNode(Unimodel):
    pass

field_factory = FieldFactory()
field_factory.add_fields(TreeNode, {
    'children': Field(types.List(types.Struct(TreeNode))),
    'data': Field(types.Struct(NodeData))})

class AllTypes(Unimodel):
    f_struct = Field(types.Struct(NodeData))
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

data = TreeNode(
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

