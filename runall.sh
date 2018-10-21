#!/bin/sh

mv ff.ini ff.ini.OLD

# ===================================================================
# Topo-only, don't fill blind pits

./run_1.sh

# ===================================================================
# Topo-only, fill blind pits

./run_2.sh

# ===================================================================
# Topo-only, fill blind pits and consider ditches/streams

./run_3.sh

# ===================================================================
mv ff.ini.OLD ff.ini
