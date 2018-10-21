#!/bin/sh

mv ff.ini ff.ini.OLD

# ===================================================================
# No Field obs, don't fill blind pits

./run_1.sh

# ===================================================================
# No Field obs, fill blind pits

./run_2.sh

# ===================================================================
# No Field obs, fill blind pits, consider ditches/streams

./run_3.sh

# ===================================================================
# No Field obs, fill blind pits, consider ditches/streams and roads

./run_4.sh

# ===================================================================
mv ff.ini.OLD ff.ini
