from unimodel.model import ModelRegistry

class Serializer(object):

    def __init__(
            self,
            model_registry=None):
        self.model_registry = model_registry or ModelRegistry()

    def serialize(self, obj):
        raise NotImplemented()

    def deserialize(self, cls, stream):
        raise NotImplemented()
