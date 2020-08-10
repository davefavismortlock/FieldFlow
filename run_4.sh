#!/bin/sh

# ===================================================================
# Field obs

echo "Datafile           : ff_data_sample_area_a4.dat" > ff.ini
echo "Text output file   : ff_a4.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_b4.dat" > ff.ini
echo "Text output file   : ff_b4.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_c4.dat" > ff.ini
echo "Text output file   : ff_c4.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_d4.dat" > ff.ini
echo "Text output file   : ff_d4.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_e4.dat" > ff.ini
echo "Text output file   : ff_e4.out" >> ff.ini
./run_ff.sh


