from unittest import TestCase, skipIf
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.serializer import JSONSerializer
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, data
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json

jsonschema = None
try:
    import jsonschema
except ImportError:
    pass

class JSONSchemaTestCase(TestCase):

    def test_simple_struct(self):
        """ serialize unicode and binary data """
        class ExampleClass(Unimodel):
            u = Field(UTF8, required=True)
            s = Field(Binary)
        
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(ExampleClass)
        self.assertTrue('u' in schema['properties'])
        self.assertEquals(schema['definitions']['ExampleClass']['required'], ['u'])
        self.assertTrue('s' in schema['properties'])

    def test_recursive_struct(self):
        """ serialize unicode and binary data """
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        # make sure dependent type NodeData present
        self.assertTrue('NodeData' in schema['definitions'])
        # check type of treenode's children
        self.assertEquals(schema['properties']['children']['type'], "array")
        self.assertEquals(schema['properties']['children']['items'].keys(), ["$ref"])

    @skipIf(jsonschema is None, "json schema validation requires the jsonschema package")
    def test_validate_schema(self):
        # based on http://sacharya.com/validating-json-using-python-jsonschema/ 
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        serializer = JSONSerializer()
        json_data = json.loads(serializer.serialize(data))
        jsonschema.validate(json_data, schema)


    @skipIf(jsonschema is None, "json schema validation requires the jsonschema package")
    def test_validate_schema(self):
        # based on http://sacharya.com/validating-json-using-python-jsonschema/ 
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(AllTypes)
        serializer = JSONSerializer()
        all_types = AllTypes(
            f_struct = NodeData(),
            f_union = NodeData(),
            f_utf8 = "asdf",
            f_binary = bin(173),
            f_int64 = 2**40,
            f_int32 = 2**28,
            f_int16 = 2**12,
            f_int8 = 4,
            f_double = 3.14,
            f_enum = 3,
            f_list = [1,2,3,4],
            f_set = set([1,2,3]),
            f_map = {"a":1}
        )
        json_data = json.loads(serializer.serialize(all_types))
        jsonschema.validate(json_data, schema)
