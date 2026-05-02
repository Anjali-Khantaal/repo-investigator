.PHONY: backend frontend mlflow test eval

backend:
	bash scripts/run_backend.sh

frontend:
	bash scripts/run_frontend.sh

mlflow:
	bash scripts/run_mlflow.sh

test:
	python -m unittest discover -s tests -v

eval:
	python scripts/evaluate_devset.py
