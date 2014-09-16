from thriftlib import *
from TFlexibleJSONProtocol import *
import pprint
import json

def print_spec(cls):
    pprint.pprint(cls.thrift_spec)

def prettyprint(json_str):
    return json.dumps(json.loads(json_str), sort_keys=True, indent=4, separators=(',', ': '))

class NodeData(ThriftModel):
    name = StringField()
    age = IntField()
    skills = MapField(StringField(), IntField())

class TreeNode(RecursiveThriftModel):
    pass

TreeNode.make_thrift_spec({
        'children': ListField(TreeNode),
        #'data': StructField(NodeData, thrift_field_name="person-data")})
        'data': StructField(NodeData)})


#print_spec(TreeNode)
print_spec(NodeData)

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
                            children=[NodeData(name="A")])
                    ],
                    data=NodeData(name="julio", age=67)
                )
            ]
       )

print data

s = serialize(data, ProtocolDebugger(TJSONProtocol.TJSONProtocolFactory(), open("write.txt", "w"), log_transport=False))
d = TreeNode.deserialize(s, ProtocolDebugger(TJSONProtocol.TJSONProtocolFactory(), open("read.txt", "w"), log_transport=False))

# this is probably false because of sorting of lists / dictionaries
print "unserialized is equal", d == data

# Verify __repr__
#print data
s = serialize(data, TFlexibleJSONProtocolFactory())
print TreeNode.deserialize(s, TFlexibleJSONProtocolFactory())
exit(1)

s = serialize_json(data)
print "JSON len(%s)" % len(s)
print prettyprint(s)

s = serialize_simplejson(data)
print "Simple JSON len(%s)" % len(s)
print prettyprint(s)

exit(1)
s = serialize_compact(data)
print "Compact len(%s)" % len(s)
print s

s = data.serialize()
print "Binary len(%s)" % len(s)
print s
s = serialize(data, ProtocolDebugger(TJSONProtocol.TJSONProtocolFactory(), open("write.txt", "w")))
d = TreeNode.deserialize(s, ProtocolDebugger(TJSONProtocol.TJSONProtocolFactory(), open("read.txt", "w")))

dynamic_serialized = DynamicObject.from_object(data).serialize()
print dynamic_serialized
print DynamicObject.deserialize(dynamic_serialized).unpack()

