.PHONY: test validate demo local
test:
	python3 -m unittest discover -s tests -v
validate: test
	python3 scripts/validate.py
demo:
	python3 -m agent.cli investigate --mode demo --incident examples/incident.json --output reports/demo.json
local:
	docker compose up --build -d
