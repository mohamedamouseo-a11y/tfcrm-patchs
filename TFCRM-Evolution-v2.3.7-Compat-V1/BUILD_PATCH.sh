#!/usr/bin/env bash
set -euo pipefail
cat \
  apply_tfcrm_evolution_v237_compat.py.part1 \
  apply_tfcrm_evolution_v237_compat.py.part2 \
  apply_tfcrm_evolution_v237_compat.py.part3 \
  > apply_tfcrm_evolution_v237_compat.py
python3 -m py_compile apply_tfcrm_evolution_v237_compat.py
chmod +x apply_tfcrm_evolution_v237_compat.py
echo "PATCH_SCRIPT_READY: apply_tfcrm_evolution_v237_compat.py"
