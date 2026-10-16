# Show-up Probability Rules

**Status:** Draft v0.2
**Scope:** Rule-based estimation of the probability that a patient attends a booked appointment.
**Consumers:** `ml/` (baseline and input features for the no-show model), `overbooking-service/` (slot-level overbooking rule), `simulation/`.

The key words MUST, MUST NOT, SHOULD and MAY are used as defined in RFC 2119.

## 1. Definitions

| Term | Definition |
|---|---|
| Appointment | A booked slot with a final outcome: `attended` or `no_show`. Cancelled and future appointments have no outcome and are excluded. |
| Reference time $T$ | The booking time of the appointment being scored. |
| History set $H_g(T)$ | All appointments of group $g$ whose appointment date is strictly before $T$ and whose outcome is known. |
| $n_g$ | Number of appointments in $H_g(T)$. |
| $s_g$ | Number of those appointments with outcome `attended`. |
| $\bar{s}$ | Global show rate over all appointments in the history set of the whole data (computed on the training period only). |
| $k$ | Smoothing strength (pseudo-count), $k \ge 0$. Default $k = 5$. |

## 2. Common Estimator (CE)

All three rules use the same estimator. Only the grouping variable differs.

**CE-1 Raw rate.** $\;r_g = s_g / n_g$ (undefined when $n_g = 0$).

**CE-2 Smoothed show probability.**

$$\hat{s}_g = \frac{s_g + k\,\bar{s}}{n_g + k}$$

**CE-3 No-show probability.** $\;\hat{p}_g = 1 - \hat{s}_g$

**CE-4 Edge cases.**
- If $n_g = 0$, the output MUST equal $\bar{s}$ (this follows from CE-2 for $k>0$).
- The raw rate (CE-1) MUST NOT be used as a model input or an overbooking input when $n_g < n_{\min}$. Default $n_{\min} = 1$ when the smoothed estimator is used.
- $\hat{s}_g$ MUST lie in $[0, 1]$.

**CE-5 Temporal integrity.** The estimator MUST use only $H_g(T)$. Appointments on or after $T$ MUST NOT contribute, including for the same patient on the same day. During training, rates MUST be computed by an expanding window over time (not over the full dataset) to avoid target leakage.

**CE-6 Output record.** Every rule MUST return the triple $(\hat{p}_g,\; n_g,\; \text{rule id})$ so consumers can judge reliability.

## 3. Rules

### R1 — Patient History

| Item | Specification |
|---|---|
| Group $g$ | One patient |
| Key | Patient identifier (`PatientId`). Names MUST NOT be used as keys. |
| Estimate | $\hat{p}_g$ from CE-3 over the patient's earlier appointments |
| No history | $n_g = 0$, output $1-\bar{s}$ |

Rationale: past attendance behaviour is the strongest individual-level signal available at booking time. Names are neither unique nor available in the public dataset, and real names are personal data.

Worked example ($k=5$, $\bar{s}=0.80$): 10 earlier appointments, 7 attended, 3 missed. Raw show rate $0.70$; smoothed $\hat{s} = (7 + 5\cdot0.80)/(10+5) = 0.733$; no-show probability $\hat{p} = 0.267$.

### R2 — Department

| Item | Specification |
|---|---|
| Group $g$ | One department / clinic specialty |
| Key | Department identifier |
| Estimate | $\hat{p}_g$ from CE-3 over all earlier appointments of the department |
| Unknown department | Output $1-\bar{s}$ with $n_g = 0$ |

Worked example ($k=0$ for illustration): ophthalmology, 100 earlier appointments, 60 attended, 40 missed. Show rate $0.60$, no-show probability $0.40$.

**Data dependency.** The public Medical Appointment No Shows dataset has no department field. R2 MUST NOT be applied to that dataset using a substitute (such as `Neighbourhood`) unless the team approves the substitution and `docs/features.md` is updated. R2 is applicable to the application's own data, where the department is stored with the appointment.

### R3 — Age Group

| Item | Specification |
|---|---|
| Group $g$ | One age band, from the table below |
| Key | Age in completed years at the appointment date |
| Estimate | $\hat{p}_g$ from CE-3 over all earlier appointments in the band |

| Band | Age (years) |
|---|---|
| A0 | $< 18$ |
| A1 | $18$–$24$ |
| A2 | $25$–$34$ |
| A3 | $35$–$54$ |
| A4 | $\ge 55$ |

Bands MUST be mutually exclusive and cover all valid ages. An age that is missing, negative or implausible (e.g. above 120) MUST be treated as invalid: the record is excluded from band statistics and the patient is scored with $1-\bar{s}$ and $n_g=0$. A0 MAY be merged into A1 if it contains fewer than $n_{\min}$ appointments after cleaning.

### R4 — Combined Estimate (cold-start rule)

R4 combines R1–R3 into a single probability and MUST be defined for every appointment, including patients with no history, patients outside the training data, and records with missing attributes. It is the rule the overbooking service calls at booking time when no trained model is available, and the fallback when the model cannot score a request.

**Step 1 — Context prior (department and age).** Work on the log-odds scale, $\operatorname{logit}(x) = \ln\frac{x}{1-x}$. Each available context rule contributes its deviation from the global rate:

$$z_0 = \operatorname{logit}(\bar{s}) \;+\; w_D\big[\operatorname{logit}(\hat{s}_D) - \operatorname{logit}(\bar{s})\big] \;+\; w_A\big[\operatorname{logit}(\hat{s}_A) - \operatorname{logit}(\bar{s})\big], \qquad \pi_0 = \frac{1}{1+e^{-z_0}}$$

where $\hat{s}_D$ is the R2 and $\hat{s}_A$ the R3 smoothed show probability. A term is omitted (its deviation set to 0) when its attribute is missing or invalid. Defaults $w_D = w_A = 1$. Values passed to $\operatorname{logit}$ MUST be clipped to $[\varepsilon, 1-\varepsilon]$ with $\varepsilon = 0.001$.

**Step 2 — Patient update.** The context prior replaces the global rate as the smoothing target of the patient's own history:

$$\hat{s}_{R4} = \frac{s_P + k_P\,\pi_0}{n_P + k_P}, \qquad \hat{p}_{R4} = 1 - \hat{s}_{R4}$$

with $s_P, n_P$ from R1 (earlier appointments only, CE-5) and $k_P$ the patient smoothing strength (default 5). The more history a patient has, the less the context prior matters.

**Cold-start behaviour (normative).**

| Situation | $n_P$ | Department | Age | Result |
|---|---|---|---|---|
| Returning patient, full data | $>0$ | known | valid | $\hat{s}_{R4}$ (history pulled towards the context prior) |
| New patient, full data | $0$ | known | valid | $\pi_0$ |
| New patient, department unknown | $0$ | unknown | valid | age-only prior |
| New patient, age unknown | $0$ | known | invalid | department-only prior |
| New patient, nothing known | $0$ | unknown | invalid | $\bar{s}$ |

A new department or age band with $n_g = 0$ already returns $\bar{s}$ through CE-4, so it adds no deviation.

**Output.** R4 MUST return $(\hat{p}_{R4},\; n_P,\; \text{source})$, where `source` is one of `patient+context`, `context`, `age`, `department`, `global`, so the consumer and the audit log know which information was used.

Worked example ($\bar{s}=0.80$, $k_P=5$): department show rate $0.60$, age band show rate $0.75$.

$$z_0 = 1.386 + (0.405 - 1.386) + (1.099 - 1.386) = 0.118, \qquad \pi_0 = 0.529$$

- New patient: $\hat{s}_{R4} = 0.529$, no-show probability $0.471$.
- Returning patient with 7 of 10 attended: $\hat{s}_{R4} = (7 + 5\cdot0.529)/(10+5) = 0.643$, no-show probability $0.357$.

**Assumption.** Adding the two log-odds deviations assumes department and age affect attendance independently. This is an approximation; it is acceptable for a rule-based baseline and MUST be checked with the calibration test in section 6. When a trained model is available it supersedes R4 for scoring, and R4 remains the fallback and the reference baseline.

## 4. Parameters

| Parameter | Default | Tuning |
|---|---|---|
| $k$ (R2, R3) | 5 | Validation set, minimising Brier score |
| $k_P$ (R1, R4) | 5 | Same |
| $w_D$, $w_A$ | 1 | Validation set; MAY be lowered if department and age overlap |
| $\varepsilon$ | 0.001 | Fixed |
| $n_{\min}$ | 1 | Optional hard threshold for consumers |
| Age band edges | 18 / 25 / 35 / 55 | Revisit after exploratory analysis |

Parameters MUST be tuned on a period earlier than the evaluation period.

## 5. Validation

Each rule is evaluated against realised outcomes on appointments later than those used to build the rates:

- AUC (ranking quality) and Brier score (probability quality),
- calibration: mean $\hat{p}$ versus observed no-show rate per probability bin,
- coverage: share of appointments scored with $n_g \ge n_{\min}$.

The rules MUST be compared with the trained no-show model on the same evaluation set (see `overbooking.md`, section 1).

R4 MUST additionally be evaluated separately on **new patients** (appointments with $n_P = 0$), since this is the case it exists for. If its calibration on that subset is poor, adjust $w_D$, $w_A$ or add an interaction term before use.

## 6. Open Decisions

| # | Decision | Options |
|---|---|---|
| 1 | Use of R1–R3 as model inputs | Separate features for the logistic regression / random forest alongside R4 (recommended) |
| 2 | Source of department for the public dataset | Not available; simulate, or drop R2 (and the department term of R4) for model training |
| 3 | Value of $k$, $k_P$, $w_D$, $w_A$ and age band edges | Tune per section 4 |
