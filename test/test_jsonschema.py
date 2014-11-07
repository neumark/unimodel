from unittest import TestCase, skipIf
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.serializer import JSONSerializer
from test.helpers import flatten
from test.fixtures import TreeNode, data
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
