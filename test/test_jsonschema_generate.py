from unittest import TestCase
from unimodel.backends.json.schema import JSONSchemaWriter
from unimodel.backends.json.generator import JSONSchemaModelGenerator
from test.helpers import flatten
from test.fixtures import TreeNode, AllTypes, NodeData, data
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json
import jsonschema

class JSONSchemaGenerate(TestCase):

    def test_simple_struct(self):
        with open("/Users/neumark/Downloads/schema.json", "r") as f:
            json_data = json.loads(f.read())
