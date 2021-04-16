#!/bin/sh

# ===================================================================
# As run 3 but woth coarse (50m) DEM

echo "Datafile           : ff_data_sample_area_a3_COARSE.dat" > ff.ini
echo "Text output file   : ff_a3_COARSE.out" >> ff.ini
./run_ff.sh

# rm -f ff.ini
# echo "Datafile           : ff_data_sample_area_b4_ALTERNATIVE.dat" > ff.ini
# echo "Text output file   : ff_b4_ALTERNATIVE.out" >> ff.ini
# ./run_ff.sh
#
# rm -f ff.ini
# echo "Datafile           : ff_data_sample_area_c4_ALTERNATIVE.dat" > ff.ini
# echo "Text output file   : ff_c4_ALTERNATIVE.out" >> ff.ini
# ./run_ff.sh
#
# rm -f ff.ini
# echo "Datafile           : ff_data_sample_area_d4_ALTERNATIVE.dat" > ff.ini
# echo "Text output file   : ff_d4_ALTERNATIVE.out" >> ff.ini
# ./run_ff.sh
#
# rm -f ff.ini
# echo "Datafile           : ff_data_sample_area_e4_ALTERNATIVE.dat" > ff.ini
# echo "Text output file   : ff_e4_ALTERNATIVE.out" >> ff.ini
# ./run_ff.sh
#
#
