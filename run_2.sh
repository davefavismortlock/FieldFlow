#!/bin/sh

# ===================================================================
# Topo-only, fill blind pits

echo "Datafile           : ff_data_sample_fields_a2.dat" > ff.ini
echo "Text output file   : ff_a2.out" >> ff.ini
./ff.py

rm -f ff.ini
echo "Datafile           : ff_data_sample_fields_b2.dat" > ff.ini
echo "Text output file   : ff_b2.out" >> ff.ini
./ff.py

rm -f ff.ini
echo "Datafile           : ff_data_sample_fields_c2.dat" > ff.ini
echo "Text output file   : ff_c2.out" >> ff.ini
./ff.py

rm -f ff.ini
echo "Datafile           : ff_data_sample_fields_d2.dat" > ff.ini
echo "Text output file   : ff_d2.out" >> ff.ini
./ff.py

rm -f ff.ini
echo "Datafile           : ff_data_sample_fields_e2.dat" > ff.ini
echo "Text output file   : ff_e2.out" >> ff.ini
./ff.py

