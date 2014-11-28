from unimodel.schema import *
from unimodel import types
import autopep8

IMPORTS = """
from unimodel.model import Unimodel, UnimodelUnion, Field, FieldFactory
from unimodel import types
"""

ALL_TEMPLATE = """
__all__ = [
%(classes)s
]"""

CLASS_DECLARATION_TEMPLATE = """
class %(name)s(Unimodel):
    pass
"""

STRUCT_DEFINITION_TEMPLATE = """
field_factory = FieldFactory()
field_factory.add_fields(%(class_name)s, {
%(field_definitions)s
})
"""

DEFAULT_INDENT = "    "
FIELD_TEMPLATE = "%(indent)s'%(name)s': Field(%(field_type)s%(field_kwargs)s)\n"
EMPTY_CLASS_BODY = "%(indent)spass\n"


class PythonSchemaWriter(object):

    """ Generates python code defining Unimodel classes
        based on the AST provided by the Schema generator. """

    def __init__(self, schema_ast):
        self.schema_ast = schema_ast
        self.compiled_structs = {}

    def get_type_name(self, field_type):
        # TODO: metadata!
        # primitive types
        if field_type.type_class.primitive_type_id is not None:
            cons = types.type_id_to_type_constructor(
                field_type.type_class.primitive_type_id)
            return "types.%s" % cons.__name__
        if field_type.type_class.parametric_type is not None:
            cons = types.type_id_to_type_constructor(
                field_type.type_class.parametric_type.type_id)
            params = [self.get_type_name(t) for t in field_type.type_class.parametric_type.type_parameters]
            return "types.%s(%s)" % (cons.__name__, ", ".join(params))
        if field_type.type_class.enum is not None:
            return "types.Enum({%s})" % ", ".join(["%s: %s" % (k, repr(v)) for k, v in field_type.type_class.enum.items()])
        if field_type.type_class.struct_name is not None:
            return "types.Struct(%s)" % field_type.type_class.struct_name
        raise Exception("Can't generate code for %s" % field_type)


    def get_field_declaration(self, field_def):
        name = field_def.common.name
        field_kwargs = [""]
        if field_def.field_id is not None:
            field_kwargs.append("field_id=%s" % field_def.field_id)
        if field_def.required:
            field_kwargs.append("required=True")
        if field_def.default is not None:
            field_kwargs.append("default=%s" % repr(field_def.default))
        field_type = self.get_type_name(field_def.field_type)
        source = FIELD_TEMPLATE % {
            'indent': DEFAULT_INDENT,
            'name': name,
            'field_type': field_type,
            # Note: field_kwargs should start with a leading comma if
            # not empty.
            'field_kwargs': " ,".join(field_kwargs)}
        return source

    def declare_struct_class(self, struct_def):
        name = struct_def.common.name
        class_source = CLASS_DECLARATION_TEMPLATE % {
            'name': name}
        return class_source

    def define_struct_fields(self, struct_def):
        class_name = struct_def.common.name
        field_definitions = [
            self.get_field_declaration(f) for f in struct_def.fields]
        if not field_definitions:
            return ""
        return STRUCT_DEFINITION_TEMPLATE % {
                'class_name': class_name,
                'field_definitions': ",\n".join(field_definitions)}

    def generate_module_source(self, run_autopep8=True):
        for struct_def in self.schema_ast.structs:
            self.compiled_structs[struct_def.common.name] = {}
        # declare classes first
        for struct_def in self.schema_ast.structs:
            source = self.declare_struct_class(struct_def)
            self.compiled_structs[struct_def.common.name]['declaration'] = source
        # add fields to the already declared classes
        for struct_def in self.schema_ast.structs:
            source = self.define_struct_fields(struct_def)
            self.compiled_structs[struct_def.common.name]['definition'] = source
        combined_source = ""
        combined_source += IMPORTS
        class_name_list = ",\n".join(["'%s'" % k for k in self.compiled_structs.keys()])
        combined_source += ALL_TEMPLATE % {'classes': class_name_list}
        for src in self.compiled_structs.values():
            combined_source += src['declaration']
        for src in self.compiled_structs.values():
            combined_source += src['definition']
        if run_autopep8:
            combined_source = autopep8.fix_code(combined_source)
        return combined_source

    def get_module(self):
        source = self.generate_module_source()
        # from http://stackoverflow.com/a/3799609
        import imp
        import sys
        module_name = self.schema_ast.common.name
        new_module = imp.new_module(module_name)
        exec source in new_module.__dict__
        sys.modules[module_name] = new_module
        return new_module
