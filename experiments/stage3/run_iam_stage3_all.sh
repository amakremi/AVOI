#!/bin/bash
# Sequentially completes Stage-3 IAM dev, val, conf. Each testbed.run_testbed call uses --skip-existing, so it is
# idempotent and safe to invoke even while a previous pass on the same partition is still finishing elsewhere or left
# a few scenarios failed (those retry automatically since they have no ground_truth file yet).
set -e
cd "$(dirname "$0")/../.."
export PYTHONPATH=.

.venv/Scripts/python.exe -u -m testbed.run_testbed --start 0 --end 512 --keep-realms 0 --skip-existing \
  --gen-config config/scenario_generator_stage3_dev.yaml --out-dir data/processed/iam_stage3_dev --id-prefix s3dev \
  >> data/manifests/testbed_stage3_dev_pass2.log 2>> data/manifests/testbed_stage3_dev_pass2.err
echo "=== dev complete ($(ls data/processed/iam_stage3_dev/ground_truth | wc -l)/512) ===" >> data/manifests/testbed_stage3_all.log

.venv/Scripts/python.exe -u -m testbed.run_testbed --start 0 --end 256 --keep-realms 0 --skip-existing \
  --gen-config config/scenario_generator_stage3_val.yaml --out-dir data/processed/iam_stage3_val --id-prefix s3val \
  --quiet-labels >> data/manifests/testbed_stage3_val.log 2>> data/manifests/testbed_stage3_val.err
echo "=== val complete ($(ls data/processed/iam_stage3_val/ground_truth | wc -l)/256) ===" >> data/manifests/testbed_stage3_all.log

.venv/Scripts/python.exe -u -m testbed.run_testbed --start 0 --end 256 --keep-realms 2 --skip-existing \
  --gen-config config/scenario_generator_stage3_conf.yaml --out-dir data/processed/iam_stage3_conf --id-prefix s3conf \
  --quiet-labels >> data/manifests/testbed_stage3_conf.log 2>> data/manifests/testbed_stage3_conf.err
echo "=== conf complete ($(ls data/processed/iam_stage3_conf/ground_truth | wc -l)/256) ===" >> data/manifests/testbed_stage3_all.log
echo "ALL IAM STAGE-3 PARTITIONS COMPLETE" >> data/manifests/testbed_stage3_all.log
