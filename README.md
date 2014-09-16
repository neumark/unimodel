To use the official thrift compiler with ThriftModels, compile the thrift file like so:

thrift  -v -out . --gen py:new_style,utf8strings,dynamic,dynimport='from thriftmodel import ThriftModel',dynbase=ThriftModel test.thrift
