from unittest import TestCase
import json
import jsonschema
from unimodel.backends.json.serializer import JSONSerializer
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.generator import JSONSchemaModelGenerator, walk_json
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, data
from unimodel.model import Unimodel, Field
from unimodel.codegen import SchemaCompiler, load_module

def print_model_schema_json(model_schema):
    serializer = JSONSerializer()
    json_data = json.loads(serializer.serialize(model_schema))
    output_json = json.dumps(
        json_data,
        sort_keys=True,
        indent=4,
        separators=(',', ': '))
    print output_json
 

class JSONSchemaGenerate(TestCase):

    def test_simple_struct(self):
        schema_writer = JSONSchemaWriter()
        schema = schema_writer.get_schema_ast(TreeNode)
        generator = JSONSchemaModelGenerator('untitled', schema)
        serializer = JSONSerializer()
        json_data = json.loads(
            serializer.serialize(
                generator.generate_model_schema()))

    def test_oneOf(self):
        # from http://json-schema.org/example2.html
        schema = json.loads("""
        {
            "id": "http://some.site.somewhere/entry-schema#",
            "$schema": "http://json-schema.org/draft-04/schema#",
            "description": "schema for an fstab entry",
            "type": "object",
            "required": [ "storage" ],
            "properties": {
                "storage": {
                    "type": "object",
                    "oneOf": [
                        { "$ref": "#/definitions/diskDevice" },
                        { "$ref": "#/definitions/diskUUID" },
                        { "$ref": "#/definitions/nfs" },
                        { "$ref": "#/definitions/tmpfs" }
                    ]
                }
            },
            "definitions": {
                "diskDevice": {},
                "diskUUID": {},
                "nfs": {},
                "tmpfs": {}
            }
        }
        """)
        generator = JSONSchemaModelGenerator('x', schema)
        model_schema = generator.generate_model_schema()
        # TODO: assertions on generated model_schema
        print_model_schema_json(model_schema)


    def test_swagger_struct(self):
        with open("/Users/neumark/git/swagger-spec/schemas/v2.0/schema.json", "r") as f:
            schema = json.loads(f.read())
        schema_name = 'swagger'

        generator = JSONSchemaModelGenerator(schema_name, schema)
        serializer = JSONSerializer()
        model_schema = generator.generate_model_schema()

        #model_schema.validate()
        json_data = json.loads(serializer.serialize(model_schema))
        output_json = json.dumps(
            json_data,
            sort_keys=True,
            indent=4,
            separators=(',', ': '))
        print output_json
        #python_source = SchemaCompiler(model_schema).generate_model_classes()
        #module = load_module(model_schema.common.name, python_source)
        #print dir(module)
