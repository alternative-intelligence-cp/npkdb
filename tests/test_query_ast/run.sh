#!/bin/bash
set -e
mkdir -p tests/test_query_ast
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_query_ast/main.npk -o tests/test_query_ast/main_bin
