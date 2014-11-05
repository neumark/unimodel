from thriftmodel.protocol import Protocol
from thriftmodel.model import ThriftModel, ThriftField, StringField

class DynamicClassNotFoundException(Exception):
    pass

class DynamicObject(ThriftModel):
    protocol = ThriftField(TType.I16)
    class_name = StringField()
    data = StringField()

    @classmethod
    def from_object(cls, obj, protocol_name_or_id=0):
        protocol = Protocol(protocol_name_or_id)
        return cls(protocol.id, obj.__class__.__name__, obj.serialize(protocol.factory))

    def unpack(self, class_hint=None, module_hint=None):
        if class_hint is not None:
            cls = class_hint
        else:
            dict_candidates = []
            if module_hint is not None:
                dict_candidates.append(sys.modules[module_hint].__dict__)
            else:
                # Use the locals of the calling stack frame
                dict_candidates.append(sys._getframe(1).f_locals)
            dict_candidates.append(globals())
            for candidate in dict_candidates:
                cls = candidate.get(self.class_name, None)
                if cls is not None:
                    return cls.deserialize(self.data, Protocol(self.protocol).factory)
        raise DynamicClassNotFoundException(self.class_name)
