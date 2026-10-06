# Model Features

**Status:** Proposal. The feature list and encoding below are proposed by the overbooking service and are final only when the prediction model is trained on them. The overbooking service follows the agreed list.

The model may only use features that are known at booking time. The overbooking service computes the same features when it calls the model.

| Feature | Source | Known at booking time | Note |
|---|---|---|---|
| `lead_days` | AppointmentDay − ScheduledDay | Yes | Days |
| `weekday` | AppointmentDay | Yes | 0 = Monday … 6 = Sunday |
| `age` | Patient record | Yes | |
| `gender_male` | Patient record | Yes | 1 = male, 0 = female |
| `scholarship` | Patient record | Yes | 0 / 1 |
| `hipertension` | Patient record | Yes | 0 / 1 |
| `diabetes` | Patient record | Yes | 0 / 1 |
| `alcoholism` | Patient record | Yes | 0 / 1 |
| `handcap` | Patient record | Yes | 0–4 |
| `prior_appt_count` | Patient's earlier appointments | Yes | Only appointments before the booking date |
| `prior_noshow_count` | Patient's earlier appointments | Yes | Only appointments before the booking date |
| `SMS_received` | — | **No** | Sent after booking; excluded |
| `Neighbourhood` | — | — | No equivalent in the application; proposed to exclude |

## Required Booking Data

To compute the features, the booking application stores the following data. The exact columns follow the agreed feature list.

| Record | Fields |
|---|---|
| Patient | Age (or date of birth), gender, scholarship, hipertension, diabetes, alcoholism, handcap |
| Appointment | Patient, appointment date, booking date, attended / no-show |

## Model Delivery

1. Train with exactly the features above, computed the same way.
2. Export into `ml/models/` with [`ml/export_model.py`](../ml/export_model.py), run from the `ml/` folder:

   ```python
   from export_model import export_model

   export_model(
       model,  # fitted classifier or Pipeline with predict_proba
       feature_names,  # list of feature names above
       version="lr-v1",
       positive_class="Yes",  # label that means no-show in the training data
       output_dir=Path("models"),
   )
   ```

3. Open a pull request with `ml/models/model.joblib` and `ml/models/feature_schema.json`.
4. The overbooking service owner copies both files into `overbooking-service/models/` and runs the overbooking service tests. `tests/test_model_acceptance.py` checks that the model loads, returns valid probabilities, matches the computed features and scores high-risk patients higher than low-risk ones.

Train with the same scikit-learn minor version as the service (see `overbooking-service/pyproject.toml`); the service logs a warning otherwise.

`ml/export_model.py` is a shared contract between the prediction model and the overbooking service; changes to it are agreed by both sides.

## Open Questions

- Final feature list and encoding
