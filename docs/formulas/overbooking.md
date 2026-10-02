# Overbooking and Model-Evaluation Formulas

**Status:** Draft proposal. These are standard formulas, **not** taken from the forecasting course. They are written down so the team can agree on them before implementing. The slot-level rule is not final until the overbooking policy is agreed.

Notation: $p_i$ = predicted no-show probability of patient $i$ (from the model), $1-p_i$ = show-up probability.

## 1. No-show model (ml/)

Logistic regression:

$$p_i = \frac{1}{1+e^{-(\beta_0 + \beta^\top x_i)}}$$

Evaluation:

- **Brier score** (calibration + sharpness): $\frac{1}{n}\sum (p_i - y_i)^2$, with $y_i=1$ for a no-show.
- **AUC:** probability that a random no-show gets a higher $p$ than a random show; computed with `sklearn.metrics.roc_auc_score`.
- **Calibration:** bin predictions, compare mean $p$ to observed no-show rate per bin (reliability curve); target: points on the diagonal.

Course link: the least-squares fitting in `forecast.md` section 6 is the linear analogue; logistic regression uses maximum likelihood instead.

## 2. Slot-level expected shows

For a slot booked with patients $1..k$ (independent, assumed):

$$E[\text{shows}] = \sum_{i=1}^{k} (1-p_i), \qquad P(\text{nobody shows}) = \prod_{i=1}^{k} p_i$$

For two patients in a slot: $P(0\text{ shows})=p_1p_2$, $P(2\text{ shows}) = (1-p_1)(1-p_2)$, $P(1\text{ show}) = 1 - p_1p_2 - (1-p_1)(1-p_2)$.

## 3. Selective overbooking rule (to be agreed)

Candidate rule: add a second patient to a slot only if the primary patient's risk exceeds a threshold $\tau$:

$$\text{overbook slot } j \iff p_j > \tau$$

Alternative: overbook until the probability that more than one patient shows up falls below a limit $\varepsilon$:

$$P(\text{shows} \ge 2) \le \varepsilon$$

$\tau$ (or $\varepsilon$) is tuned in the simulation by trading off waiting time against idle time and overtime.

## 4. KPIs (see `docs/kpi-definitions.md`)

$$\text{Utilization} = \frac{\text{physician busy time}}{\text{planned session length}}$$

Waiting time $=$ consultation start $-\max(\text{appointment time}, \text{arrival time})$. Idle time and overtime as defined there.

For the simulation comparison (fixed-interval vs. overbooked) report the mean and a confidence interval over $R$ independent replications:

$$\bar{x} \pm t_{\alpha/2,R-1}\frac{s}{\sqrt{R}}$$

Course link: forecast-accuracy measures (MAD, MAPE) from `forecast.md` section 2 apply when comparing predicted vs. observed daily no-show counts.
