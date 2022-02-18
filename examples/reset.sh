#!/bin/bash
pip install --no-deps ../
reentry scan
verdi daemon restart
