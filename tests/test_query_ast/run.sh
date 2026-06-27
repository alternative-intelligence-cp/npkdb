#!/bin/bash
set -e
mkdir -p test_query_ast
/home/randy/Workspace/REPOS/nitpick/build/npkc test_query_ast/main.npk -o test_query_ast/main_bin
