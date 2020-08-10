#!/bin/sh

# ===================================================================
# Field obs, alternatives

echo "Datafile           : ff_data_sample_area_a4_ALTERNATIVE.dat" > ff.ini
echo "Text output file   : ff_a4_ALTERNATIVE.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_b4_ALTERNATIVE.dat" > ff.ini
echo "Text output file   : ff_b4_ALTERNATIVE.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_c4_ALTERNATIVE.dat" > ff.ini
echo "Text output file   : ff_c4_ALTERNATIVE.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_d4_ALTERNATIVE.dat" > ff.ini
echo "Text output file   : ff_d4_ALTERNATIVE.out" >> ff.ini
./run_ff.sh

rm -f ff.ini
echo "Datafile           : ff_data_sample_area_e4_ALTERNATIVE.dat" > ff.ini
echo "Text output file   : ff_e4_ALTERNATIVE.out" >> ff.ini
./run_ff.sh


