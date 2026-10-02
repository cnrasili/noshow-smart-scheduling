# Overbooking Rule and Model-Evaluation Formulas

**Status:** Draft v0.2. Sections 1, 2 and 5 are standard formulas, **not** taken from the forecasting course. Section 3 adapts the airline overbooking approach to a clinic slot. Costs and caps are parameters to be agreed and tuned in the simulation.

The key words MUST, MUST NOT, SHOULD and MAY are used as defined in RFC 2119.

Notation: $p_i$ = no-show probability of patient $i$ and $s_i = 1-p_i$ = show-up probability. $p_i$ comes from the trained model, or from rule R4 in [`rules.md`](rules.md) when no model is available.

## 1. No-show model (ml/)

Logistic regression:

$$p_i = \frac{1}{1+e^{-(\beta_0 + \beta^\top x_i)}}$$

Evaluation:

- **Brier score** (calibration and sharpness): $\frac{1}{n}\sum (p_i - y_i)^2$, with $y_i=1$ for a no-show.
- **AUC:** probability that a random no-show receives a higher $p$ than a random show; `sklearn.metrics.roc_auc_score`.
- **Calibration:** bin the predictions and compare mean $p$ with the observed no-show rate per bin; points should lie on the diagonal. Overbooking decisions use $p$ as a probability, so calibration matters more than AUC.

Course link: least-squares fitting in `forecast.md` section 6 is the linear analogue; logistic regression uses maximum likelihood.

## 2. Show-up count of a slot

A slot has capacity $C$ (default $C=1$ patient) and $k$ booked patients. The number of patients who show up is $S_k = \sum_{i=1}^{k} B_i$ with $B_i \sim \text{Bernoulli}(s_i)$, independent and with different $s_i$ (Poisson-binomial distribution).

$$E[S_k] = \sum_{i=1}^{k} s_i, \qquad P(S_k = 0) = \prod_{i=1}^{k} p_i$$

The full distribution is computed exactly by dynamic programming, adding one patient at a time:

$$P_{j}(m) = P_{j-1}(m)\,p_j + P_{j-1}(m-1)\,s_j, \qquad P_0(0) = 1$$

and the quantity used by the rule is

$$q_k = P(S_k \ge C) = \sum_{m \ge C} P_k(m).$$

Independence is an assumption. It MUST be checked in the simulation (for example when patients of one family or one referral book together).

## 3. Overbooking rule

### 3.1 Background: airline practice

An airline sells $N$ tickets for $C$ seats and accepts that some passengers do not show up. Three approaches exist:

1. **Expected-value cap.** Choose $N$ so that the expected number of arrivals equals capacity, $N \cdot p \le C$. With $p=0.95$ and $C=220$ this gives $N = 220/0.95 \approx 231.6$, so at most 231 tickets. It ignores the variance of arrivals.
2. **Cost balance.** Sell one more ticket as long as the expected cost of denied boarding is smaller than the expected cost of an empty seat. This is the critical-fractile (newsvendor / Littlewood-type) logic.
3. **Simulation and learning.** Monte Carlo simulation and models with passenger-level probabilities set the limit per flight, typically about 5–10 % above capacity.

The clinic rule below is approach 2 applied to a slot, using approach 1 as a simple baseline and approach 3 (our discrete-event simulation) to tune the costs.

### 3.2 Cost model

For a slot with $k$ bookings the expected cost is

$$\text{Cost}(k) = c_I\, E\big[(C - S_k)^+\big] + c_W\, E\big[(S_k - C)^+\big]$$

| Symbol | Meaning | Unit |
|---|---|---|
| $c_I$ | Cost of one unused unit of capacity (physician idle for one slot) | minutes (weight) |
| $c_W$ | Cost of one patient above capacity (waiting and overtime caused by an extra patient) | minutes (weight) |
| $r = c_W / c_I$ | Cost ratio, the only cost parameter the rule depends on | — |

Both costs SHOULD be expressed in the minute-based KPIs of `docs/kpi-definitions.md` so that the rule and the simulation use the same units.

### 3.3 Decision rule R5-A (cost-based, primary)

Adding a patient $k+1$ with show-up probability $s_{k+1}$ changes the expected cost by

$$\Delta = s_{k+1}\Big[\,c_W\, P(S_k \ge C) \;-\; c_I\, P(S_k \le C-1)\Big].$$

A patient is added to the slot if and only if $\Delta < 0$, which simplifies to

$$\boxed{\;q_k = P(S_k \ge C) \;<\; \frac{c_I}{c_I + c_W} = \frac{1}{1+r}\;}$$

The candidate's own probability $s_{k+1}$ cancels out of the condition: it only scales the size of the gain or loss, not its sign. The decision therefore depends on the patients already in the slot.

This is the precise form of the airline statement "overbook while P(arrivals above capacity) × compensation cost is smaller than the empty-seat opportunity cost".

**Special case $C=1$, one booked patient (no-show probability $p$).** The rule reduces to a threshold on that patient's risk:

$$\text{overbook the slot} \iff p > \tau, \qquad \tau = \frac{c_W}{c_I + c_W} = \frac{r}{1+r}$$

Derivation check: with one patient the expected cost is $c_I p$; with a second patient (no-show probability $p_2$) it is $c_I p p_2 + c_W (1-p)(1-p_2)$; the second is smaller exactly when $p > \tau$.

### 3.4 Procedure

For each slot, in order of booking:

1. Compute the show-up probabilities $s_i$ of the patients already booked (R4 or model).
2. Compute $q_k = P(S_k \ge C)$ with the dynamic programme of section 2.
3. If $q_k < 1/(1+r)$ **and** the caps of section 3.5 allow it, the slot MAY accept one more booking; otherwise it MUST NOT.
4. After a booking is added, repeat from step 1 for the same slot.

A slot with no booking is always open for its first patient.

### 3.5 Caps and safeguards (MUST)

| Cap | Default | Rationale |
|---|---|---|
| Maximum bookings per slot, $k_{\max}$ | 2 | Prevents queues from compounding; the airline rule of thumb is 5–10 % over capacity |
| Maximum overbooked slots per session, $\rho$ | 10 % of session slots | Session-level analogue of the airline cap |
| Minimum quality of $p$ | $p$ comes from a calibrated model or R4 | An uncalibrated $p$ makes $q_k$ meaningless |
| No overbooking when the slot's patients all have $n_P = 0$ and source `global` | — | No information about the patients; fall back to a single booking |

If any input is missing, the rule MUST fall back to a single booking per slot.

### 3.6 Baseline rule R5-B (expected-value cap)

The airline baseline for comparison in the simulation: keep adding patients while the expected number of arrivals stays within capacity,

$$\text{add patient } k+1 \iff \sum_{i=1}^{k} s_i < C.$$

It needs no costs but ignores the variability of $S_k$, so it is expected to overbook too much when the $s_i$ are close to 0.5 and too little when they are close to 1.

### 3.7 Worked examples ($C=1$)

| Case | Inputs | Result |
|---|---|---|
| $r = 1$ ($\tau = 0.5$), patient with $p = 0.60$ | $q_1 = 0.40 < 0.50$ | Overbook |
| $r = 1$, patient with $p = 0.30$ | $q_1 = 0.70 \ge 0.50$ | Do not overbook |
| $r = 0.5$ ($\tau = 1/3$), patient with $p = 0.40$ | $q_1 = 0.60$, limit $1/1.5 = 0.667$ | Overbook |
| $r = 1$, two patients with $p = 0.60$ each | $q_2 = 1 - 0.36 = 0.64 \ge 0.50$ | No third booking (also blocked by $k_{\max}=2$) |
| R5-B, $s_1 = 0.4$ | $\sum s = 0.4 < 1$ | Add a second patient |
| R5-B, $s_1 = 0.4$, $s_2 = 0.4$ | $\sum s = 0.8 < 1$ | Add a third (blocked by $k_{\max}$) |

### 3.8 Parameter tuning

$r$, $k_{\max}$ and $\rho$ are tuned in the discrete-event simulation: for a grid of values, run $R$ replications per setting and choose the setting that improves waiting time and idle time against fixed-interval booking without exceeding the agreed overtime limit. The rule is judged only against these simulated KPIs, not against the formula's own expected cost.

## 4. KPIs (see `docs/kpi-definitions.md`)

$$\text{Utilization} = \frac{\text{physician busy time}}{\text{planned session length}}$$

Waiting time $=$ consultation start $-\max(\text{appointment time}, \text{arrival time})$. Idle time and overtime as defined there.

For the simulation comparison (fixed-interval vs. overbooked) report the mean and a confidence interval over $R$ independent replications:

$$\bar{x} \pm t_{\alpha/2,R-1}\frac{s}{\sqrt{R}}$$

Course link: forecast-accuracy measures (MAD, MAPE) from `forecast.md` section 2 apply when comparing predicted and observed daily no-show counts.

## 5. Open Decisions

| # | Decision | Options |
|---|---|---|
| 1 | Capacity of a slot $C$ and slot length | 1 patient per slot (default); depends on the simulation design |
| 2 | Cost ratio $r = c_W/c_I$ | Start at 1; tune in the simulation; may differ per department |
| 3 | $k_{\max}$ and $\rho$ | 2 and 10 % as starting points |
| 4 | Independence of patients' attendance | Assume; test in the simulation |
| 5 | Linearity of the waiting cost | The rule treats every extra patient as costing $c_W$; if queues grow convexly, replace $c_W$ by a delay function fitted from the simulation |
