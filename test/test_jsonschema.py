from unittest import TestCase
from unimodel.backends.json.schema import JSONSchemaWriter
from test.helpers import flatten
from test.fixtures import TreeNode, data
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json

class JSONSchemaTestCase(TestCase):

    def test_simple_struct(self):
        """ serialize unicode and binary data """
        class ExampleClass(Unimodel):
            u = Field(UTF8, required=True)
            s = Field(Binary)
        
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(ExampleClass)
        self.assertTrue('u' in schema['properties'])
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
