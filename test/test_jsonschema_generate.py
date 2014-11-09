from unittest import TestCase
import json
import jsonschema
from unimodel.backends.json.serializer import JSONSerializer
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.generator import JSONSchemaModelGenerator
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, data
from unimodel.model import Unimodel, Field
from unimodel.codegen import SchemaCompiler, load_module

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
        schema_name = 'swagger'
        generator = JSONSchemaModelGenerator(schema_name, schema)
        serializer = JSONSerializer()
        ast = generator.generate_model_schema()
        import pdb;pdb.set_trace()
        json_data = json.loads(serializer.serialize(ast))
        print generator.unparsed.keys()
        output_json = json.dumps(
            json_data,
            sort_keys=True,
            indent=4,
            separators=(',', ': '))
        python_source = SchemaCompiler(ast).generate_model_classes()
        module = load_module(ast.common.name, python_source)
        print dir(module)
