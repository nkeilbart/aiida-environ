#!/bin/bash
pip install --use-feature=in-tree-build ../../ # --no-deps ../../
reentry scan
verdi daemon restart
verdi run wc_test.py
while true  
do  
  verdi process list -p1 -a  
  sleep 180  
done