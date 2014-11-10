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
        model_schema = generator.generate_model_schema()
        
        #header = [s for s in model_schema.structs if s.common.name == 'header'][0]
        #print [f for f in header.fields if f.common.name == 'items'][0]
        model_schema.validate()
        return
        json_data = json.loads(serializer.serialize(model_schema))
        output_json = json.dumps(
            json_data,
            sort_keys=True,
            indent=4,
            separators=(',', ': '))
        print output_json
        #python_source = SchemaCompiler(model_schema).generate_model_classes()
        module = load_module(model_schema.common.name, python_source)
        print dir(module)
