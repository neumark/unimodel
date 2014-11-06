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


