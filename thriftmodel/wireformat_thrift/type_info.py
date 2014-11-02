from thrift.Thrift import TType

class ThriftTypeInfo(object):

    def __init__(
            self,
            type_id,
            annotations=None,
            is_binary=False,
            is_union=False):
        self.type_id = type_id
        self.annotations = annotations
        self.is_binary = is_binary
        self.is_union = is_union
        # This refence is set in the constructor
        # of FieldType
        self.field_type = None

    def type_name(self):
        name = TType._VALUES_TO_NAMES[self.type_id].lower()
        if self.field_type.type_parameters:
            name += "<%s>" % ", ".join([t.type_name() for t in self.field_type.type_parameters])
        return name

class StructWrapper(object):
    """ A wrapper around unimodels to provide thrift-specific methods like
        read() and write() """

    def __init__(self, obj):
        super(StructWrapper, self).__init__(obj)
        self._obj = obj
        
    def __getattr__(self, attrib):
        return getattr(self._obj, attrib)

    def write(self, *args, **kwargs):
        import pdb;pdb.set_trace()

class ThriftSpecFactory(object):

    def __init__(self, model_registry):
        self.model_registry = model_registry
        self._spec_cache = {}

    def get_spec(self, struct_class):
        if struct_class not in self._spec_cache:
            self._spec_cache[struct_class] = self.get_spec_for_struct(struct_class)
        return self._spec_cache[struct_class]

    def get_spec_for_struct(self, struct_class):
        field_list = sorted(struct_class._fields_by_name.values(), key=lambda x: x.field_id)
        thrift_spec = [None]
        # save the spec to cache so recurisve data structures work.
        self._spec_cache[struct_class] = thrift_spec
        for f in field_list:
            thrift_spec.append(self.get_spec_for_field(f))
        return thrift_spec

    def get_spec_type_parameter(self, field_type):
        """ Returns value 3 of the element in thrift_spec which defines this field. """
        # structs are a special case
        if field_type.thrift_type_info.type_id == TType.STRUCT:
            interface_class = field_type.python_type
            implementation_class = self.model_registry.lookup(interface_class)
            return (implementation_class, self.get_spec(implementation_class))
        # If there are no type parameters, return None
        if not field_type.type_parameters:
            return None
        # lists, sets, maps
        spec_list = []
        for t in field_type.type_parameters:
            # for each type_parameter, first add the type's id
            spec_list.append(t.thrift_type_info.type_id)
            # then the type's parameters
            spec_list.append(self.get_spec_type_parameter(t))
        return spec_list

    def get_spec_for_field(self, field):
        return (
            field.field_id,
            field.field_type.thrift_type_info.type_id,
            field.field_name,
            self.get_spec_type_parameter(field.field_type),
            field.default,)

