from unimodel.model import ModelRegistry

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
