from unimodel.schema import *

IMPORTS = """
from unimodel.model import Unimodel, Field
from unimodel import types
"""

CLASS_TEMPLATE = """
class %(name)s(Unimodel):
%(fields)s
"""

FIELD_TEMPLATE = "    %(name)s = Field(%(field_type)s%(field_kwargs)s)\n"
EMPTY_CLASS_BODY = "    pass\n"


class SchemaCompiler(object):

    """ Generates python code defining Unimodel classes
        based on the AST provided by the Schema generator. """

    def __init__(self, model_schema):
        self.model_schema = model_schema
        self.compiled_structs = {}

    def get_type_name(self, field_type):
        # TODO: STUB
        return "types.Int"

    def get_field_declaration(self, field_def):
        name = field_def.common.name
        # When we change the name, we need to record
        # the original name too.
        # TEMPORARY HACK (just to try out compilation)
        if name in ['in', '$ref']:
            name = "a"
        field_kwargs = ""
        field_type = self.get_type_name(field_def.field_type)
        source = FIELD_TEMPLATE % {
            'name': name,
            'field_type': field_type,
            # Note: field_kwargs should start with a leading comma if
            # not empty.
            'field_kwargs': field_kwargs}
        return source

    def generate_struct_class(self, struct_def):
        name = struct_def.common.name
        field_definitions = [
            self.get_field_declaration(f) for f in struct_def.fields]
        if not field_definitions:
            field_definitions = [EMPTY_CLASS_BODY]
        class_source = CLASS_TEMPLATE % {
            'name': name,
            'fields': "".join(field_definitions)}
        return class_source

    def generate_model_classes(self):
        for struct_def in self.model_schema.structs:
            class_source = self.generate_struct_class(struct_def)
            self.compiled_structs[struct_def.common.name] = class_source
        combined_source = ""
        combined_source += IMPORTS
        for src in self.compiled_structs.values():
            combined_source += src
        return combined_source


def load_module(module_name, source):
    # from http://stackoverflow.com/a/3799609
    import imp
    import sys
    new_module = imp.new_module(module_name)
    exec source in new_module.__dict__
    sys.modules[module_name] = new_module
    return new_module
