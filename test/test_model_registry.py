from unittest import TestCase
from test.helpers import flatten
from test.fixtures import TreeNode, data
from unimodel.model import Unimodel, Field
from unimodel.types import *
import json
from unimodel.model import ModelRegistry
from unimodel.backends.json.serializer import JSONSerializer, JSONValidationException

class ModelRegistryTestCase(TestCase):
    """ Demonstrates the use of the model registry.
        The idea is that a bare-bones "interface class"
        (one presumably generated or constructed at runtime
        from some sort of schema) can be swapped out with an
        "implementation class" with a rich set of model methods """
        

    def test_implementation_class(self):
        """ serialize unicode and binary data """
        class NestedIface(Unimodel):
            x = Field(Int)

        class OuterIface(Unimodel):
            u = Field(UTF8, required=True)
            s = Field(Binary)
            nested = Field(Struct(NestedIface))

        class OuterImpl(OuterIface):
            def useful_method(self):
                return len(self.u or '') + len(self.s or '')

        class NestedImpl(NestedIface):

            CONST = 7

            def another_method(self, x):
                return self.CONST * x

        model_registry = ModelRegistry()
        model_registry.register(NestedIface, NestedImpl)
        model_registry.register(OuterIface, OuterImpl)

        data = OuterIface(u="asdf", s="jj", nested=NestedIface(x=7))
        serializer = JSONSerializer(model_registry=model_registry)
        s = serializer.serialize(data)
        data_read = serializer.deserialize(OuterIface, s)
        self.assertEquals(data_read.__class__, OuterImpl)
        self.assertEquals(data_read.nested.__class__, NestedImpl)
        # methods of impl classes can be called
        self.assertEquals(data_read.useful_method(), 6)
        self.assertEquals(data_read.nested.another_method(1), 7)
