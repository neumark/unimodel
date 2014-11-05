class Serializer(object):

    def serialize(self, obj):
        raise NotImplemented()

    def deserialize(self, cls, stream):
        raise NotImplemented()
