from datapilot.monitoring.timeline import build_timeline

run_id = "local__905b72a592"
timeline = build_timeline(run_id)

for event in timeline:
    print(event)
