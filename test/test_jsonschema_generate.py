from unittest import TestCase
import json
import jsonschema
from unimodel.backends.json.serializer import JSONSerializer
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.generator import JSONSchemaModelGenerator
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, data
from unimodel.model import Unimodel, Field
from unimodel.codegen import SchemaCompiler

class JSONSchemaGenerate(TestCase):

    def test_simple_struct(self):
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        generator = JSONSchemaModelGenerator('untitled', schema)
        serializer = JSONSerializer()
        json_data = json.loads(serializer.serialize(generator.generate_model_schema()))


    def test_simple_struct(self):
        with open("/Users/neumark/git/swagger-spec/schemas/v2.0/schema.json", "r") as f:
            schema = json.loads(f.read())
        generator = JSONSchemaModelGenerator('untitled', schema)
        serializer = JSONSerializer()
        ast = generator.generate_model_schema()
        json_data = json.loads(serializer.serialize(ast))
        print generator.unparsed.keys()
        output_json = json.dumps(
            json_data,
            sort_keys=True,
            indent=4,
            separators=(',', ': '))
        print SchemaCompiler(ast).generate_model_classes()
