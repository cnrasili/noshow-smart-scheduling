# Statistical Quality Control Formulas

**Source:** Statistical Quality Control course notes: introduction (DMAIC), modelling process quality, inferences about process quality, methods of statistical process control, control charts for variables and for attributes, process capability analysis, with the factor tables.

**Status:** Draft. Items marked *(standard)* are not shown in the lecture text that was extracted but are the usual form of the same method; check them against the slides before the report.

## 1. Principles

- A process is **in statistical control** when measurements vary randomly inside control limits; points outside the limits or systematic patterns point to an **assignable cause**.
- Three-sigma limits: for a statistic $w$ with mean $\mu_w$ and standard deviation $\sigma_w$,

$$UCL=\mu_w+3\sigma_w,\qquad CL=\mu_w,\qquad LCL=\mu_w-3\sigma_w$$

A false alarm has probability $\alpha\approx 0.0027$ per point, so the average run length without a real shift is $ARL_0=1/\alpha\approx 370$ *(standard)*.

- **Phase I:** estimate $CL$ and limits from 20–25 preliminary samples (trial limits). Investigate points outside the limits; remove those with an assignable cause and recompute until the process is stable. **Phase II:** use the fixed limits to monitor new data.

## 2. Control charts for variables

Samples of size $n$ (usually 4–6), $m$ samples (at least 20–25). $\bar{\bar{x}}$ = mean of sample means, $\bar{R}$ = mean range, $R=x_{\max}-x_{\min}$.

| Chart | Center line | Limits |
|---|---|---|
| $\bar{x}$ | $\bar{\bar{x}}$ | $\bar{\bar{x}}\pm A_2\bar{R}$ |
| $R$ | $\bar{R}$ | $LCL=D_3\bar{R}$, $UCL=D_4\bar{R}$ |

The standard deviation is estimated by $\hat\sigma=\bar{R}/d_2$. Factors $A_2$, $D_3$, $D_4$, $d_2$ come from the factor table (appendix). For $n=5$: $A_2=0.577$, $D_3=0$, $D_4=2.114$, $d_2=2.326$. Build the $R$ chart first, since the $\bar{x}$ limits depend on the variability being stable.

Worked example in the notes (wafer thickness, $n=5$, $m=25$): $\bar{\bar{x}}=1.5056$, $\bar{R}=0.32521$; $R$ chart $UCL=2.114\times0.32521=0.687$, $LCL=0$; $\bar{x}$ chart $UCL=1.5056+0.577\times0.32521=1.693$.

*Use:* monitoring the session KPIs (mean waiting time, physician idle time, overtime) of the live system, with one session or one week as a sample.

## 3. Control charts for attributes

Fraction nonconforming, based on the binomial distribution: $D\sim Bin(n,p)$, $\hat{p}=D/n$, $E[\hat{p}]=p$, $Var(\hat{p})=p(1-p)/n$.

With $m$ preliminary samples of size $n$ and $D_i$ nonconforming in sample $i$:

$$\hat{p}_i=\frac{D_i}{n},\qquad \bar{p}=\frac{\sum D_i}{mn},\qquad UCL,\,LCL=\bar{p}\pm3\sqrt{\frac{\bar{p}(1-\bar{p})}{n}}$$

If $LCL<0$ it is set to 0. For samples of different sizes $n_i$, the limits are computed per sample with $n_i$ *(standard)*. Worked example in the notes: orange juice cans, $n=50$, $m=30$; samples 15 and 23 above $UCL$ because of a new raw material and a new operator; after removing them, sample 21 is still above the limit with no cause found and is kept; a later adjustment lowers $\bar{p}$, and a formal hypothesis test on the two $\bar{p}$ values confirms the improvement.

Other attribute charts *(standard)*: $np$ chart ($n\bar{p}\pm3\sqrt{n\bar{p}(1-\bar{p})}$), $c$ chart (count of defects, $\bar{c}\pm3\sqrt{\bar{c}}$), $u$ chart ($\bar{u}\pm3\sqrt{\bar{u}/n}$).

*Use:* the **daily no-show rate** is a fraction nonconforming: a "nonconforming" unit is an appointment that was missed.

## 4. Process capability

Natural tolerance limits: $\mu\pm3\sigma$ (99.73 % of a normal process, 0.27 % outside = 2700 per million). Capability ratio with specification limits $LSL$, $USL$:

$$C_p=\frac{USL-LSL}{6\sigma},\qquad \hat\sigma=\frac{\bar{R}}{d_2}$$

One-sided limits and off-center processes *(standard)*:

$$C_{pu}=\frac{USL-\mu}{3\sigma},\qquad C_{pl}=\frac{\mu-LSL}{3\sigma},\qquad C_{pk}=\min(C_{pu},C_{pl})$$

Example in the notes: $USL-LSL=1.00$, $\hat\sigma=0.1398$, $C_p=1.192$, so the process uses about $1/C_p=83.9\%$ of the specification width.

Capability analysis assumes a normal, stable process. Check normality with a probability plot (informal) and with the Anderson–Darling, Ryan–Joiner (similar to Shapiro–Wilk) or Kolmogorov–Smirnov tests. A histogram needs at least 100 observations.

*Use:* waiting time and overtime have an upper specification only (the limits used for the template comparison: mean wait ≤ 5 min, mean overtime ≤ 5 min), so $C_{pu}$ applies. Waiting times are skewed and not normal, so a capability index must not be reported without a normality check.

## 5. Monitoring the no-show model: a p chart on the data

Phase I on the training period (22 appointment days up to 2016-06-01, about 4,100 appointments per day): $\bar{p}=0.2061$, limits $\bar{p}\pm3\sqrt{\bar{p}(1-\bar{p})/n_i}\approx0.187$–$0.225$.

| Finding | Value |
|---|---|
| Phase I days outside the limits | 8 of 22: six above the upper limit (4 to 20 May, 22.5–23.5 %) and two below the lower limit (31 May and 1 June, 17.9–18.2 %) |
| Phase II (2 to 8 June, 5 days) | 4 of 5 days below the lower limit; rate 17.3–19.7 % |

Interpretation:
- The process is **not in statistical control in Phase I**: day-to-day variation exceeds what the binomial model predicts (overdispersion, because the daily mix of lead times and patients changes). Limits from the plain $p$ chart are too narrow; a chart with adjusted limits (for example the Laney $p'$ chart *(standard)*) or limits from the observed day-to-day spread should be used before using it as an alarm.
- The drop of the rate from the end of May, from about 22 % to 18 %, is visible on the chart. It explains why all models over-predict on the test week (calibration-in-the-large, `overbooking.md`) and why a train/test split by time is more demanding than a random split.
- For small persistent shifts, a CUSUM or EWMA chart is more sensitive than a Shewhart chart *(standard; not in the extracted lecture text)*.

**Proposed monitoring** for the live service: a daily $p$ chart (adjusted limits) for the no-show rate, a weekly calibration check (mean predicted risk against observed rate, `overbooking.md` section 1), and an $\bar{x}$/$R$ chart for the session KPIs. A sustained signal triggers recalibration of the model.
