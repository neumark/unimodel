from unimodel.model import ModelRegistry
import datetime


class Serializer(object):

    def __init__(
            self,
            validate_before_write=True,
            model_registry=None):
        self.validate_before_write = validate_before_write
        self.model_registry = model_registry or ModelRegistry()

    def serialize(self, obj):
        raise NotImplementedError()

    def deserialize(self, cls, stream):
        raise NotImplementedError()


class SchemaWriter(object):
    """ A schemawriter gets a SchemaAST object and produces a 
        schema (jsonschema, thrift, python code). """

    def __init__(
            self,
            ast,
            model_registry=None):
        self.ast = ast
        self.model_registry = model_registry or ModelRegistry()

    def get_schema(self):
        raise NotImplementedError()

class SchemaReader(object):
    """ A schemareader gets an external schema (thrift, jsonschema
    or python code) and outputs the corresponding SchemaAST
    datastructure. """

    def get_ast(self):
        raise NotImplementedError()
