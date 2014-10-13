#!/usr/bin/env bash
# generate python code
thrift -gen py:new_style,utf8strings,dynamic -out test test/compiled/thrift/test_resources.thrift
# generate json description
thrift -gen json -out test/compiled/json test/compiled/thrift/test_resources.thrift
python -m json.tool test/compiled/json/test_resources.json > test/compiled/json/test_resources_pp.json
mv test/compiled/json/test_resources_pp.json test/compiled/json/test_resources.json
