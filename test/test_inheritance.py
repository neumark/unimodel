from unittest import TestCase
from unimodel.model import Unimodel, Field
from unimodel import types

class ModelInheritanceTestCase(TestCase):

    def test_simple_inheritance(self):
        class Base(Unimodel):
            a = Field(types.UTF8)
    
        class Child(Base):
            b = Field(types.Int)

        self.assertEquals(1, len(Base.get_field_definitions()))
        self.assertEquals(2, len(Child.get_field_definitions()))
