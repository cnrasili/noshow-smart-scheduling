# Show-up Probability Rules

**Status:** Draft. Three rule-based estimates of the probability that a patient shows up. They serve as a baseline and as input features for the no-show model; how they are combined is still open (see the end of this file).

Notation: $y=1$ means no-show, $y=0$ means the patient came. For a group $g$ with $n_g$ past appointments of which $s_g$ were attended:

$$\text{show rate}_g = \frac{s_g}{n_g}, \qquad p^{\text{noshow}}_g = 1 - \text{show rate}_g$$

## General conditions (apply to all rules)

1. **Only past appointments count.** To score an appointment booked at time $T$, use only appointments that happened before $T$. Using later ones leaks the answer into the model (same rule as `prior_appt_count` in `docs/features.md`).
2. **Small groups are smoothed.** A raw rate from few appointments is unreliable (1 of 1 attended gives 100%). Use a prior with the global show rate $\bar{s}$ and a strength $k$:

$$\hat{s}_g = \frac{s_g + k\,\bar{s}}{n_g + k}$$

   With $n_g=0$ the estimate equals the global rate; with large $n_g$ it approaches the raw rate. Start with $k=5$ and tune on validation data.
3. **Report $n_g$ with every rate** so the overbooking service can tell a reliable estimate from a weak one.

## Rule 1: Patient history

Group = one patient, identified by the dataset's patient ID. The patient's name must not be used: names are not unique, the public dataset has none, and real names are personal data.

Example: 10 past appointments, 7 attended, 3 missed, $k=5$, $\bar{s}=0.80$:

$$\text{raw}=0.70, \qquad \hat{s} = \frac{7 + 5\cdot 0.80}{10+5} = 0.733$$

A patient with no history gets the global rate (the smoothing formula handles this).

## Rule 2: Department

Group = department (e.g. ophthalmology: 100 booked, 60 attended, 40 missed gives a raw show rate of 0.60 and no-show rate of 0.40). Same formula and smoothing as above, with $s_g, n_g$ counted over all patients of that department.

**Data warning:** the public Medical Appointment No Shows dataset has **no department/specialty column**. The closest field is `Neighbourhood`, which `docs/features.md` proposes to exclude. This rule needs either a department field in the application's own (simulated) data, or a different grouping variable for the public dataset. Decide before building it.

## Rule 3: Age group

Group = age band. The bands in the request overlap at the boundaries (18–24, 24–35), so the proposal uses non-overlapping bands and adds the missing ages:

| Band | Ages |
|---|---|
| 0 | under 18 |
| 1 | 18–24 |
| 2 | 25–34 |
| 3 | 35–54 |
| 4 | 55 and over |

Same formula and smoothing, counted per band. Data cleaning: the public dataset contains invalid ages (negative values); remove or flag them before computing bands. The under-18 band is kept so that no patient is left without a group; it can be merged with 18–24 if it turns out too small or not useful.

## Open decisions

- **Combining the three rules.** Options: use each as a separate feature in the logistic regression / random forest (recommended, the model learns the weights); take a weighted average; or use the patient rule when $n_g$ is large and fall back to department/age otherwise.
- **Smoothing strength $k$** and the **age band edges**.
- **Department source** (see Rule 2).
- The rule-based estimates should be compared against the model with AUC and calibration (`overbooking.md`, section 1), computed on later appointments than the ones used to build the rates.
