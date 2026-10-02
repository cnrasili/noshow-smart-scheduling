# Statistics Formulas

**Source:** Statistics course notes: descriptive statistics, hypothesis testing (one and two samples, variances), correlation, simple and multiple linear regression. Textbooks in the notes folder are references only.

**Status:** Draft. Section 4 lists tests run on the cleaned appointment data. Items marked *(standard)* are not in the course notes but are the usual form of the same method.

Notation: $\alpha$ = significance level, $H_0$ = null hypothesis, $\bar{x}$, $s$ = sample mean and standard deviation.

## 1. Hypothesis testing

- A test splits the sample space into a **critical region** (reject $H_0$) and its complement.
- **Type I error:** reject $H_0$ when it is true; probability $\alpha$. **Type II error:** keep $H_0$ when it is false; probability $\beta$. Power $=1-\beta$.
- Decision by critical value, or by $p$-value: reject if $p<\alpha$. Not rejecting $H_0$ does not prove it.

| Test | Statistic | Reject $H_0$ (two-sided) |
|---|---|---|
| One mean, $\sigma$ known or $n$ large | $z=\dfrac{\bar{x}-\mu_0}{\sigma/\sqrt{n}}$ | $\lvert z\rvert > z_{\alpha/2}$ |
| One mean, $\sigma$ unknown, normal | $t=\dfrac{\bar{x}-\mu_0}{s/\sqrt{n}}$, $df=n-1$ | $\lvert t\rvert > t_{\alpha/2,\,n-1}$ |
| Two means, independent, $n_1,n_2\ge 30$ | $z=\dfrac{(\bar{x}_1-\bar{x}_2)-\delta_0}{\sqrt{s_1^2/n_1+s_2^2/n_2}}$ | $\lvert z\rvert > z_{\alpha/2}$ |
| Two means, small, equal variances | $t=\dfrac{(\bar{x}_1-\bar{x}_2)-\delta_0}{s_p\sqrt{1/n_1+1/n_2}}$, $s_p^2=\dfrac{(n_1-1)s_1^2+(n_2-1)s_2^2}{n_1+n_2-2}$, $df=n_1+n_2-2$ | $\lvert t\rvert > t_{\alpha/2,\,n_1+n_2-2}$ |
| One variance | $\chi^2=\dfrac{(n-1)s^2}{\sigma_0^2}$, $df=n-1$ | $\chi^2>\chi^2_{\alpha/2}$ or $<\chi^2_{1-\alpha/2}$ |
| Two variances | $F=\dfrac{s_1^2}{s_2^2}$, $df=(n_1-1,\,n_2-1)$ | $F>F_{\alpha/2}$ or $<F_{1-\alpha/2}$ |

Large-sample confidence interval for a difference of means: $(\bar{x}_1-\bar{x}_2)\pm z_{\alpha/2}\sqrt{s_1^2/n_1+s_2^2/n_2}$; if it does not cover 0 the means differ, and the interval also gives the size of the difference.

**Two proportions** *(standard; the notes do not include it)*: with $\hat{p}=\dfrac{x_1+x_2}{n_1+n_2}$,

$$z=\frac{\hat{p}_1-\hat{p}_2}{\sqrt{\hat{p}(1-\hat{p})\left(\frac1{n_1}+\frac1{n_2}\right)}}$$

*Use in the project:*
- Is a booking policy or template better than another? The simulation produces paired per-session differences; a one-sample $t$ or $z$ test on the differences (or the equivalent confidence interval) is what the dashboard shows.
- Reminder A/B comparison: two-proportion test on the no-show rates of the two arms.
- Does a patient attribute (gender, age group, new vs returning) change the no-show rate? Two-proportion test, see section 4.
- Is the service-time variability the assumed one? One-variance $\chi^2$ test on measured consultation times.

## 2. Correlation and simple linear regression

$$r=\frac{S_{xy}}{\sqrt{S_{xx}S_{yy}}},\qquad -1\le r\le 1,\qquad S_{xx}=\sum(x_i-\bar{x})^2,\; S_{xy}=\sum(x_i-\bar{x})(y_i-\bar{y})$$

Model $\hat{y}=\hat\beta_0+\hat\beta_1x$:

$$\hat\beta_1=\frac{S_{xy}}{S_{xx}},\qquad \hat\beta_0=\bar{y}-\hat\beta_1\bar{x},\qquad \hat\sigma^2=MSE=\frac{SSE}{n-2},\qquad se(\hat\beta_1)=\sqrt{\frac{\hat\sigma^2}{S_{xx}}}$$

$$SST=SSR+SSE,\qquad R^2=\frac{SSR}{SST}=1-\frac{SSE}{SST}=r^2,\qquad F_0=\frac{MSR}{MSE}\;(df=1,\,n-2),\qquad t_0=\frac{\hat\beta_1}{se(\hat\beta_1)}$$

Reject $H_0:\beta_1=0$ if $\lvert t_0\rvert>t_{\alpha/2,\,n-2}$ (equivalent to the $F$ test).

## 3. Multiple linear regression

$$y=X\beta+\varepsilon,\qquad \hat\beta=(X^\top X)^{-1}X^\top y,\qquad \hat\sigma^2=\frac{SSE}{n-k-1}$$

with $k$ predictors. Adjusted $R^2=1-\dfrac{SSE/(n-k-1)}{SST/(n-1)}$ *(standard)*.

*Use in the project:* linear regression is the base of `forecast.md` section 6 (trend) and of the linear probability view of the no-show model. The no-show model itself is logistic regression, which is fitted by maximum likelihood and not by these least-squares formulas; $R^2$ does not apply to it (AUC, Brier score and calibration are used instead, see `overbooking.md`).

## 4. Tests run on the cleaned appointment data

Training period (appointments up to 2016-06-01), two-proportion tests on the no-show rate:

| Comparison | No-show rates | Difference | $z$ | $p$ |
|---|---|---|---|---|
| Male vs female | 20.2 % vs 20.8 % | −0.6 pp | −2.01 | 0.044 |
| Age under 25 vs 55+ | 23.1 % vs 16.2 % | +7.0 pp | 19.8 | < 0.001 |
| Lead time ≥ 15 days vs ≤ 2 days | 33.6 % vs 9.0 % | +24.6 pp | 76.7 | < 0.001 |
| New vs returning patients | 22.2 % vs 15.5 % | +6.7 pp | 20.8 | < 0.001 |
| SMS received vs not | 28.0 % vs 17.5 % | +10.5 pp | 35.1 | < 0.001 |

Reading:
- **Gender** is borderline significant at 5 % and the difference is 0.6 percentage points. With about 88,000 appointments almost any difference becomes "significant", so effect size matters more than $p$. Gender is practically irrelevant for prediction here, which supports leaving it out of rule R2 (`rules.md`).
- Age, lead time and patient history show large and clear differences, in line with the model importances.
- The **SMS** difference is large but in the wrong direction for a causal reading: SMS was sent to patients who were already at higher risk (long lead times). It must not be used as an estimate of the reminder effect.
