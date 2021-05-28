# `aiida-environ`

This plugin builds on top of [aiida-quantumespresso](https://github.com/aiidateam/aiida-quantumespresso). 

## Compatibility
Currently tested with aiida-core~1.6 and aiida-quantumespresso~3.4

## Installation
Currently installable from source:

    https://gitlab.com/mat_av147/aiida-environ
    pip install aiida-environ

## License
See the `LICENSE.txt` file for more details.

## Developer Notes
To patch a file from its QE parent, consider using a

`git diff tag1 tag2 -- file > patch_file`

`patch -p1 target patch_file`

## Acknowlegements