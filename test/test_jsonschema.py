from unittest import TestCase
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.serializer import JSONSerializer
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, tree_data, all_types_data
from unimodel.model import Unimodel, Field
from unimodel.types import *
from unimodel.metadata import Metadata
import json
import jsonschema


class JSONSchemaTestCase(TestCase):

    def test_simple_struct(self):
        """ serialize unicode and binary data """
        class ExampleClass(Unimodel):
            u = Field(UTF8, required=True)
            s = Field(Binary)

        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(ExampleClass)
        self.assertTrue('u' in schema['properties'])
        self.assertEquals(
            schema['definitions']['ExampleClass']['required'],
            ['u'])
        self.assertTrue('s' in schema['properties'])

    def test_recursive_struct(self):
        """ serialize unicode and binary data """
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        # make sure dependent type NodeData present
        self.assertTrue('NodeData' in schema['definitions'])
        # check type of treenode's children
        self.assertEquals(schema['properties']['children']['type'], "array")
        self.assertEquals(
            schema['properties']['children']['items'].keys(),
            ["$ref"])

    def test_recursive_struct(self):
        """ serialize unicode and binary data """
        from unimodel.backends.json.type_data import MDK_FIELD_NAME

        NAME = "/-/"

        class A(Unimodel):
            a = Field(Map(UTF8, Int), metadata=Metadata(
                backend_data={'json': {MDK_FIELD_NAME: NAME}}))

        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(A)
        # make sure dependent type NodeData present
        self.assertEquals(schema['properties'].keys(), [NAME])

    def test_validate_recursive_schema(self):
        # based on http://sacharya.com/validating-json-using-python-jsonschema/
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        serializer = JSONSerializer()
        json_data = json.loads(serializer.serialize(tree_data))
        jsonschema.validate(json_data, schema)

    def test_validate_all_types(self):
        # based on http://sacharya.com/validating-json-using-python-jsonschema/
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(AllTypes)
        serializer = JSONSerializer()
        for ix in xrange(0, len(all_types_data)):
            json_data = json.loads(serializer.serialize(all_types_data[ix]))
            jsonschema.validate(json_data, schema)
