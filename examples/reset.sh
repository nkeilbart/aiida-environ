#!/bin/bash
pip install --use-feature=in-tree-build --no-deps ../
reentry scan
verdi daemon restart
