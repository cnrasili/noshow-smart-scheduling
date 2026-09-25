# No-Show Prediction Model

Data preparation and training of the no-show prediction model.

## Tech Stack

- Python 3.12
- pandas for data preparation
- scikit-learn for logistic regression, random forest, AUC and calibration
- joblib for exporting the model
- Jupyter and matplotlib for analysis

## Scope

- Cleaning and exploratory analysis of the Medical Appointment No Shows dataset
- Feature engineering (see [model features](../docs/features.md))
- Logistic regression and random forest models
- Evaluation with AUC and calibration
- Exporting the selected model for the overbooking service

## Data

Place the downloaded dataset in `data/raw/`. Raw and processed data are not committed.

## Development

```bash
python -m venv .venv
pip install -r requirements.txt
jupyter lab
```

## Exporting the Model

Export the selected model with `export_model.py`. It writes `model.joblib` and `feature_schema.json` into `overbooking-service/models/`. The steps and the required features are in [model features](../docs/features.md).
