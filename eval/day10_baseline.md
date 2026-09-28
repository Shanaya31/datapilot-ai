# DataPilot AI — Day 10 Evaluation Baseline

- Failure cases: 8/8
- Diagnosis accuracy: 100%
- Evidence grounding rate: 100%
- Pipeline failed as expected: 100%
- Average investigation latency: 397.91 seconds
- Total evaluation time: 527.9 seconds

All eight injected failure categories were correctly diagnosed:
null_spike, stale_data, low_volume, api_failure, schema_change,
invalid_values, duplicate_spike, pipeline_timeout.

No prompt iteration was required after the baseline evaluation.
The main follow-up item is investigation latency, especially for
pipeline_timeout and low_volume cases.
