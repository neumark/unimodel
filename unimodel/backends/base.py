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

    def __init__(
            self,
            name=None,
            description=None,
            struct_classes=None):
        self.name = name or "untitled"
        self.description = description or "generated %s" % str(datetime.datetime.now)
        self.struct_classes = struct_classes or set()

    def get_schema_ast(self):
        raise NotImplementedError()

    def get_schema_text(self):
        raise NotImplementedError()

