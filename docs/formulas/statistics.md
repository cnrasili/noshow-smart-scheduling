# Statistics Formulas

**Source:** Probability and Statistics course notes (weeks 1–11, sampling distributions, estimation and confidence intervals). The three textbooks in the notes folder (Miller & Freund, two Schaum's outlines) are used only as references.

**Status:** Draft. Section 6 lists the checks made against the calculations already used in the project.

Notation: $\theta$ = probability of success in a Bernoulli trial, $\bar{X}$ = sample mean, $S^2$ = sample variance.

## 1. Sampling and the central limit theorem

For a random sample $X_1,\dots,X_n$ (independent, identically distributed) with mean $\mu$ and variance $\sigma^2$:

$$\bar{X}=\frac1n\sum X_i,\qquad S^2=\frac{\sum (X_i-\bar{X})^2}{n-1},\qquad E[\bar{X}]=\mu,\qquad Var(\bar{X})=\frac{\sigma^2}{n}$$

Central limit theorem: $Z=\dfrac{\bar{X}-\mu}{\sigma/\sqrt{n}}$ is approximately standard normal for large $n$.

*Use:* the replications of the simulation are a random sample of sessions; averages over replications are normally distributed.

## 2. Confidence intervals

Mean, $\sigma$ known (or $n$ large):

$$\bar{x} \pm z_{\alpha/2}\frac{\sigma}{\sqrt n}$$

Mean, $\sigma$ unknown, normal population ($n$ small):

$$\bar{x} \pm t_{\alpha/2,\,n-1}\frac{s}{\sqrt n}$$

Variance of a normal population:

$$\frac{(n-1)s^2}{\chi^2_{\alpha/2,\,n-1}} < \sigma^2 < \frac{(n-1)s^2}{\chi^2_{1-\alpha/2,\,n-1}}$$

Common values: $z_{0.05}=1.645$, $z_{0.025}=1.96$, $z_{0.005}=2.576$.

Sample size for a margin of error $E$ (mean): $\;n \ge \left(\dfrac{z_{\alpha/2}\,\sigma}{E}\right)^2$.

*Use:* every "mean ± CI" in the simulation reports (`clinic_sim.py`, dashboard, templates) is $\bar{x} \pm 1.96\,s/\sqrt{n}$ with $n = 1000$ replications; for such $n$, $t \approx z$. For paired differences between policies, the same formula is applied to the per-session differences.

## 3. Probability rules

$$P(A\cup B)=P(A)+P(B)-P(A\cap B),\qquad P(B\mid A)=\frac{P(A\cap B)}{P(A)},\qquad P(A\cap B)=P(A)\,P(B\mid A)$$

Independent events: $P(A\cap B)=P(A)P(B)$.

Total probability and Bayes' theorem, for a partition $A_1,\dots,A_k$:

$$P(B)=\sum_j P(B\mid A_j)P(A_j),\qquad P(A_i\mid B)=\frac{P(B\mid A_i)P(A_i)}{\sum_j P(B\mid A_j)P(A_j)}$$

*Use:* the slot model assumes that patients' attendances are independent events. Bayes' theorem is the basis for updating a patient's no-show risk when new information arrives.

## 4. Distributions

| Distribution | Probability function | Mean / variance | Use in the project |
|---|---|---|---|
| Bernoulli($\theta$) | $\theta^x(1-\theta)^{1-x}$, $x\in\{0,1\}$ | $\theta$ / $\theta(1-\theta)$ | One patient shows up ($\theta = 1-p_i$) |
| Binomial($n,\theta$) | $\binom{n}{x}\theta^x(1-\theta)^{n-x}$ | $n\theta$ / $n\theta(1-\theta)$ | Shows among $n$ patients with the same risk; airline model |
| Poisson($\lambda$) | $\dfrac{\lambda^x e^{-\lambda}}{x!}$ | $\lambda$ / $\lambda$ | Arrival counts; approximation of rare events |
| Geometric($\theta$) | $\theta(1-\theta)^{x-1}$ | $1/\theta$ / $(1-\theta)/\theta^2$ | Number of bookings until the first no-show |
| Exponential($\lambda$) | $\lambda e^{-\lambda x}$, $x>0$ | $1/\lambda$ / $1/\lambda^2$ | Service times with high variability (CV = 1) |
| Normal($\mu,\sigma^2$) | $\dfrac{1}{\sigma\sqrt{2\pi}}e^{-(x-\mu)^2/2\sigma^2}$ | $\mu$ / $\sigma^2$ | Attendance count at session level; arrival offset |

Normal approximation to the binomial, with continuity correction:

$$P(X\le x)\approx \Phi\!\left(\frac{x+0.5-n\theta}{\sqrt{n\theta(1-\theta)}}\right)$$

It is reasonable when $n\theta$ and $n(1-\theta)$ are both at least about 5–10.

The attendance count of one slot with different risks $p_1,\dots,p_k$ is **not** binomial but Poisson-binomial; it is computed exactly in `overbooking.md`, section 2, and reduces to the binomial when all $p_i$ are equal.

## 5. Expectation, variance and covariance

$$E[aX+bY]=aE[X]+bE[Y],\qquad Var(aX+b)=a^2Var(X)$$

$$Cov(X,Y)=E[XY]-E[X]E[Y],\qquad \rho=\frac{Cov(X,Y)}{\sigma_X\sigma_Y},\qquad Var(X+Y)=Var(X)+Var(Y)+2\,Cov(X,Y)$$

*Use:* if patients' attendance is positively correlated (families, shared transport), the variance of the show-up count is larger than under independence, so the slot probabilities $q_k$ of the overbooking rule are too optimistic.

## 6. Checks against the project's calculations

| Calculation in the project | Check | Result |
|---|---|---|
| Poisson-binomial dynamic programme (`overbooking.md` §2, `clinic_sim.cost_rule`) | Equal risks must give the binomial distribution | Matches (difference $<10^{-15}$) |
| Smoothing $\hat{s}=\dfrac{s+k\bar{s}}{n+k}$ (`rules.md`) | Posterior mean of a Beta–Binomial model with prior $\text{Beta}(k\bar{s},\,k(1-\bar{s}))$: $\dfrac{s+a}{n+a+b}$ with $a+b=k$ | Identical; $k$ is the prior's pseudo-count and can be read as "equivalent number of prior appointments" |
| CIs in simulation outputs | $\bar{x}\pm1.96\,s/\sqrt{n}$, $n=1000$ | Valid by the CLT; $t_{0.025,999}=1.962$ |
| Number of replications | $n\ge(z\sigma/E)^2$. For the paired waiting-time difference of the threshold-0.30 policy $s=4.65$ min | $E=0.25$ min needs about 1,330 sessions; $E=0.1$ min about 8,300. The current 1,000 gives about ±0.29 min |
| Service-time distribution | Course distribution is the exponential (CV = 1); the simulation uses a lognormal with CV = 0.5 | **Sensitive:** with exponential service times the fixed-interval waiting rises from 2.3 to 7.8 min and overtime from 2.9 to 10.4 min; the extra patients seen by overbooking stay +2.8, but the extra waiting rises from +4.5 to +6.3 min. The real CV must be measured |

## 7. Not covered by the course notes

Confidence interval for a proportion (Wald or Wilson interval for show rates of small groups), the Beta–Binomial model itself, the Poisson-binomial distribution, and bootstrap intervals (used for the AUC) are not in the course notes. They are standard, but a reference should be cited in the report; the Miller & Freund textbook in the notes folder covers inference on proportions.
