#!/bin/sh

# ===================================================================
# Topo-only, fill blind pits and consider ditches/streams

echo "Datafile           : ff_data_sample_area_a3.dat" > ff.ini
echo "Text output file   : ff_a3.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_b3.dat" > ff.ini
echo "Text output file   : ff_b3.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_c3.dat" > ff.ini
echo "Text output file   : ff_c3.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_d3.dat" > ff.ini
echo "Text output file   : ff_d3.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_e3.dat" > ff.ini
echo "Text output file   : ff_e3.out" >> ff.ini
./run_ff.sh

