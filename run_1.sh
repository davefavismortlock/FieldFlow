#!/bin/sh

# ===================================================================
# Topo-only, don't fill blind pits

echo "Datafile           : ff_data_sample_area_a1.dat" > ff.ini
echo "Text output file   : ff_a1.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_b1.dat" > ff.ini
echo "Text output file   : ff_b1.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_c1.dat" > ff.ini
echo "Text output file   : ff_c1.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_d1.dat" > ff.ini
echo "Text output file   : ff_d1.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_e1.dat" > ff.ini
echo "Text output file   : ff_e1.out" >> ff.ini
./run_ff.sh
