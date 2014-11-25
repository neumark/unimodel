from unittest import TestCase
from unimodel.backends.python.schema_reader import PythonSchemaReader
from unimodel.backends.python.schema_writer import PythonSchemaWriter
from test.fixtures import TreeNode, AllTypes, NodeData, A, TestUnion, tree_data, all_types_data


class PythonSchemaReaderTestCase(TestCase):

    def test_single_struct(self):
        """ Make a StructDef out of a Unimodel class """
        schema_reader = PythonSchemaReader(NodeData)
        ast = schema_reader.get_ast()
        self.assertEquals(ast.root_struct_name, NodeData.get_name())
        self.assertEquals(len(ast.structs), 1)
        self.assertEquals(ast.structs[0].common.name, NodeData.get_name())
        # once python code generation works, we can generate code from
        # the ast, and then compare our ast with the ast we get from
        # the generated code (they should be the same).

    def test_all_fields(self):
        schema_reader = PythonSchemaReader(AllTypes)
        ast = schema_reader.get_ast()
        self.assertEquals(ast.root_struct_name, AllTypes.get_name())
        struct_names = sorted(
            [s.common.name for s in ast.structs])
        expected_struct_names = sorted([
            AllTypes.get_name(),
            NodeData.get_name(),
            A.get_name(),
            TestUnion.get_name()])
        self.assertEquals(
                struct_names, expected_struct_names)

    def test_recursive_datatype(self):
        """ tests whether ASTs can be built
        for recursive data types. """
        schema_reader = PythonSchemaReader(TreeNode)
        ast = schema_reader.get_ast()
        self.assertEquals(ast.root_struct_name, TreeNode.get_name())
        struct_names = sorted(
            [s.common.name for s in ast.structs])
        expected_struct_names = sorted([
            TreeNode.get_name(),
            NodeData.get_name()])
        self.assertEquals(
                struct_names, expected_struct_names)

    def test_manually_added(self):
        """ tests whether dependant structs are detected
            and pulled into the schema """
        schema_reader = PythonSchemaReader(
                NodeData,
                struct_classes=[A])
        ast = schema_reader.get_ast()
        self.assertEquals(ast.root_struct_name, NodeData.get_name())
        struct_names = sorted(
            [s.common.name for s in ast.structs])
        expected_struct_names = sorted([
            A.get_name(),
            NodeData.get_name()])
        self.assertEquals(
                struct_names, expected_struct_names)

    def test_read_write_identical_fields(self):
        """ Class -> AST -> Class should yield same fields """
        schema_reader = PythonSchemaReader(NodeData)
        ast = schema_reader.get_ast()
        schema_writer = PythonSchemaWriter(ast)
        module = schema_writer.get_module()
        self.assertTrue(hasattr(module, 'NodeData'))
        # assert field names are the same
        self.assertEquals(
                sorted([f.field_name for f in NodeData.get_field_definitions()]),
                sorted([f.field_name for f in module.NodeData.get_field_definitions()]))
        # assert field types are the same
        for field in NodeData.get_field_definitions():
            field_name = field.field_name
            self.assertEquals(
                    field.field_type.get_type_name(),
                    module.NodeData.get_field_definition(field_name).field_type.get_type_name())

    def test_read_write_identical_all_types(self):
        """ Class -> AST -> Class works for all field types """
        schema_reader = PythonSchemaReader(AllTypes)
        ast = schema_reader.get_ast()
        schema_writer = PythonSchemaWriter(ast)
        print schema_writer.generate_module_source()
        module = schema_writer.get_module()
        self.assertTrue(hasattr(module, 'AllTypes'))

