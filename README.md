# Outpatient Appointment System: No-Show Prediction and Smart Scheduling

Outpatient clinics lose capacity when patients miss their appointments without notice, while overbooking every slot uniformly leads to congestion, long waiting times and physician overtime. This project builds a working appointment booking application in which a machine learning model estimates each patient's no-show probability at booking time. Slots are overbooked selectively, only where the no-show risk is high, and patients receive automated confirmation and reminder messages. The resulting schedules are evaluated with discrete-event simulation to show that both patient waiting time and physician idle time improve compared with fixed-interval booking, and the system reports utilization, idle time and overtime on an admin dashboard.

The project is developed as an interdisciplinary study combining industrial engineering (appointment template design, overbooking policy, simulation) and computer engineering (web application, model-serving API, reminder engine).

## System Overview

```
[Web application] --HTTP--> [Overbooking service]
                                 |-- Feature builder --> No-show model --> p_noshow
                                 |-- Overbooking rule engine
                                 |-- Reminder scheduler
                                 |-- A/B assignment and logging
                                 `-- KPI calculator --> Admin dashboard
                                          |
                                   [Shared database]

[Simulation] <-- no-show probabilities + overbooking rule
```

## Repository Structure

| Folder | Content |
|---|---|
| [`web/`](web/) | Appointment web application, patient and doctor interfaces, database, calendar/slot algorithm |
| [`overbooking-service/`](overbooking-service/) | Model-serving REST API, overbooking rule engine, reminder jobs, A/B logging, KPI dashboard |
| [`ml/`](ml/) | Data preparation, no-show prediction model (logistic regression / random forest), AUC and calibration |
| [`simulation/`](simulation/) | Appointment template, overbooking policy, Arena discrete-event simulation |
| [`docs/`](docs/) | Shared contracts between components: API, model features, KPI definitions |

## Dataset

The prediction model is trained on the public [Medical Appointment No Shows](https://www.kaggle.com/datasets/joniarroba/noshowappointments) dataset (Hoppen, 2016), which contains about 110,000 appointments from public clinics in Vitória, Brazil.

The dataset is **not** stored in this repository. To use it:

1. Download the dataset from Kaggle.
2. Place the CSV file in `ml/data/raw/`.

The dataset is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) by its author and is used for non-commercial academic purposes only.

## Shared Contracts

Components depend on each other through the documents in [`docs/`](docs/).

| Document | Between |
|---|---|
| [API contract](docs/api-contract.md) | Web application and overbooking service |
| [Model features](docs/features.md) | Prediction model and overbooking service |
| [KPI definitions](docs/kpi-definitions.md) | Simulation and KPI dashboard |

## Workflow

- `main` always contains working code.
- Work on a feature branch, for example `feature/predict-api`, and merge through a pull request.
- Commit messages are one line in the form `type: Imperative short message`, for example `feat: Add prediction endpoint` or `fix: Correct lead time calculation`.
- Never commit secrets. Copy `.env.example` to `.env` and fill in local values.
- Arena model files are binary and cannot be merged. Only one person edits a model file at a time.

## Course

LMMF405 Interdisciplinary Project, Fall 2026–2027, Department of Industrial Engineering (Eng), Istanbul Arel University.

## License

The source code is released under the [MIT License](LICENSE). The dataset is subject to its own license (see [Dataset](#dataset)).

## References

Hoppen, J. (2016). *Medical appointment no shows* [Data set]. Kaggle. https://www.kaggle.com/datasets/joniarroba/noshowappointments
