#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_document_crud/main.npk -o tests/test_document_crud/main_bin
./tests/test_document_crud/main_bin
