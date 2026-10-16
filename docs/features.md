# Model Features

**Status:** Agreed. The delivered prediction model (`random_forest-v1` in `ml/models/`) is trained on exactly the features and encodings below, and the overbooking service computes the same ones.

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
| `prior_appt_count` | Patient's earlier appointments: dataset history and bookings in the application | Yes | Only appointments before the booking date |
| `prior_noshow_count` | Patient's earlier appointments: dataset history and bookings in the application | Yes | Only appointments before the booking date |
| `SMS_received` | — | **No** | Sent after booking; excluded |
| `Neighbourhood` | — | — | No equivalent in the application; excluded |

## Dataset Rules

Agreed on 15 October 2026. The public Medical Appointment No Shows dataset is the project's single data source.

- Patients, their attributes and their appointment history come from the dataset. No patient or record is invented.
- Patients are identified by the dataset's `PatientId`. National ID numbers (T.C. kimlik numarası) are not used, not even fictional ones, under the Turkish data protection law (KVKK).
- A column added to fit the project, such as department or doctor, holds the same value in every row and never changes the existing values. All appointments in the dataset belong to one department and one doctor.
- Rows that cannot be stored as they are, as in the prediction model's cleaning step, are left out: 5 rows whose appointment day is before the booking day and 1 row with age −1. The project uses the remaining 110,521 appointments of 62,298 patients.
- A patient's gender, scholarship, health attributes and neighbourhood are the same in all of their rows; the age differs by at most one year. The patient record takes the age of the patient's latest appointment.

## Required Booking Data

To compute the features, the booking application stores the following data. The exact columns follow the agreed feature list.

| Record | Fields |
|---|---|
| Patient | Dataset `PatientId`, age (or date of birth), gender, scholarship, hipertension, diabetes, alcoholism, handcap |
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
4. The overbooking service owner installs the model with `python -m overbooking_service.install_model` (see the [overbooking service README](../overbooking-service/README.md#installing-a-delivered-model)). The command checks that the model loads, matches the computed features, returns valid probabilities and scores high-risk patients higher than low-risk ones, and replaces the installed model only when every check passes. `tests/test_model_acceptance.py` runs the same checks on the installed model.

Train with the same scikit-learn minor version as the service (see `overbooking-service/pyproject.toml`); the service logs a warning otherwise.

`ml/export_model.py` is a shared contract between the prediction model and the overbooking service; changes to it are agreed by both sides.
