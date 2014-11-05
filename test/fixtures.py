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

