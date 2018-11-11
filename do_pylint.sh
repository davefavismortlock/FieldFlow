#!/bin/bash

#pylint --errors-only --extension-pkg-whitelist="PyQt4, qgis"   ff.py gui.py initialize.py layers.py readinput.py searches.py shared.py simulate.py simulationthread.py utils.py > err.txt

pylint --max-line-length=700 --indent-string="   " --disable="bad-whitespace, missing-docstring" --module-naming-style=any --const-naming-style=any --class-naming-style=any --function-naming-style=any --method-naming-style=any --attr-naming-style=any --argument-naming-style=any --variable-naming-style=any --class-attribute-naming-style=any --inlinevar-naming-style=any --extension-pkg-whitelist="PyQt4, qgis"   ff.py gui.py initialize.py layers.py readinput.py searches.py shared.py simulate.py simulationthread.py utils.py > err.txt

