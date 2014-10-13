#!/usr/bin/env bash
# generate python code
thrift -gen py:new_style,utf8strings,dynamic -out . test_resources/thrift/test_resources.thrift
# generate json description
thrift -gen json -out test_resources/json test_resources/thrift/test_resources.thrift
