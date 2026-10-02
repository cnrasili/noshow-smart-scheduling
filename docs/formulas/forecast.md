# Forecast Formulas

**Source:** LIEN315 Forecasting Theory (FT02–FT06 lecture slides). Notation follows the course: $D_t$ = observed value, $F_t$ = forecast for period $t$ made in $t-1$, $e_t = D_t - F_t$.

**Status:** Draft. Each entry lists where it is likely to be used in the project; confirm before implementing.

## 1. Descriptive statistics (FT02)

Sample mean and variance:

$$\bar{X} = \frac{\sum X_i}{n}, \qquad S^2 = \frac{\sum (X_i-\bar{X})^2}{n-1}, \qquad S = \sqrt{S^2}$$

*Use:* summarising simulated service times, waiting times and no-show rates.

## 2. Forecast accuracy (FT03, FT04)

$$e_t = D_t - F_t$$

| Measure | Formula | Note |
|---|---|---|
| MAD | $\frac{1}{n}\sum \lvert e_t \rvert$ | Same unit as the series |
| MSE | $\frac{1}{n}\sum e_t^2$ | Penalises large errors; RMSE $=\sqrt{MSE}$ |
| MAPE | $\frac{1}{n}\sum \frac{\lvert e_t \rvert}{D_t}$ | Scale-free; undefined when $D_t=0$ |
| MPE | $\frac{1}{n}\sum \frac{e_t}{D_t}$ | Detects bias; unbiased means $E[e_t]=0$ |

Rule of thumb from the slides: $\sigma_e \approx 1.25 \times MAD$ for normally distributed errors.

*Use:* comparing forecasts of daily demand / daily no-show rate (ML and simulation reports).

## 3. Autocorrelation and randomness tests (FT03, FT06)

Lag-$k$ autocorrelation:

$$r_k = \frac{\sum_{t=k+1}^{n} (D_t-\bar{D})(D_{t-k}-\bar{D})}{\sum_{t=1}^{n} (D_t-\bar{D})^2}$$

Standard error and confidence limits (random series: $SE \approx 1/\sqrt{n}$ for $r_1$):

$$SE(r_k) = \sqrt{\frac{1 + 2\sum_{i=1}^{k-1} r_i^2}{n}}, \qquad r_k \in 0 \pm t \cdot SE(r_k)$$

Test of a single coefficient: $H_0:\rho_k=0$, statistic $t = r_k / SE(r_k)$.

Ljung–Box (modified Box–Pierce) $Q$ test for the first $m$ lags:

$$Q_m = n(n+2)\sum_{k=1}^{m} \frac{r_k^2}{n-k}, \qquad \text{reject } H_0 \text{ if } Q_m > \chi^2_{\alpha}(m)$$

Excel: `CHISQ.INV.RT(alpha, m)`. Example from the slides: $\chi^2_{0.05}(10)=18.307$.

Pattern reading: trend → large $r_k$ for the first lags, decaying slowly; seasonality → significant $r_k$ at the seasonal lag (4 quarterly, 12 monthly; for weekday patterns, 7 on daily data).

*Use:* checking for weekday seasonality in no-show rates; checking that model residuals are white noise.

## 4. Stationarity and trend tests (FT04)

**Runs test.** $R$ = number of runs above/below the median; $m = n/2$ ($n$ even) or $(n-1)/2$ ($n$ odd). Small sample ($m\le 20$): reject $H_0$ if $R \le R_L$ or $R \ge R_U$ (table). Large sample:

$$z = \frac{R-\mu_R}{\sigma_R}, \qquad \mu_R = m+1, \qquad \sigma_R = \sqrt{\frac{m(m-1)}{2m-1}}$$

Reject if $\lvert z\rvert \ge z_{\alpha/2}$.

**Daniels' test (trend).** Spearman's rank correlation between $t$ and $D_t$:

$$r_s = 1 - \frac{6\sum d_t^2}{n(n^2-1)}, \quad d_t = t - R(D_t), \qquad z = \frac{r_s}{1/\sqrt{n-1}} \;(n>30)$$

**von Neumann ratio.**

$$M = \frac{SS_{\Delta y}}{SS_{yy}} = \frac{\frac{1}{n-1}\sum (y_t-y_{t-1})^2}{\frac{1}{n}\sum (y_t-\bar{y})^2}$$

$M\approx 2$: random; $M<2$: trend or positive autocorrelation; $M>2$: negative autocorrelation. Critical values: $M_{1-\alpha/2}$ (table), upper limit $4 - M_{1-\alpha/2}$.

*Use:* deciding whether a stationary method (section 5) is adequate.

## 5. Stationary series: moving average and exponential smoothing (FT04)

Moving average of order $N$:

$$F_{t} = \frac{1}{N}\sum_{i=t-N}^{t-1} D_i, \qquad F_{t+1} = F_t + \frac{1}{N}(D_t - D_{t-N})$$

Simple exponential smoothing, $0<\alpha\le 1$:

$$F_t = \alpha D_{t-1} + (1-\alpha)F_{t-1} = F_{t-1} + \alpha e_{t-1}$$

Weights: $\alpha(1-\alpha)^{i-1}$. Recommended $\alpha \in [0.1, 0.2]$ for production use. Initial forecast: average of the first ~10 observations.

Equivalent parameters (same average age of data):

$$\frac{N+1}{2} = \frac{1}{\alpha} \;\Rightarrow\; \alpha = \frac{2}{N+1}, \quad N = \frac{2-\alpha}{\alpha}$$

*Use:* baseline forecast of the clinic's daily no-show rate / daily demand.

## 6. Trend: linear regression and Holt's method (FT05)

Least squares for $\hat{Y} = a + bX$:

$$b = \frac{SS_{xy}}{SS_{xx}}, \quad SS_{xx} = n\sum x_i^2 - \left(\sum x_i\right)^2, \quad SS_{xy} = n\sum x_i y_i - \sum x_i \sum y_i, \quad a = \bar{y} - b\bar{x}$$

Holt's double exponential smoothing (level $S_t$, slope $G_t$, usually $\beta \le \alpha$):

$$S_t = \alpha D_t + (1-\alpha)(S_{t-1}+G_{t-1}), \qquad G_t = \beta (S_t - S_{t-1}) + (1-\beta) G_{t-1}$$

$$F_{t,t+\tau} = S_t + \tau G_t$$

Initial values can come from a regression fit on the baseline data.

## 7. Seasonality (FT05)

Seasonal factors $c_t$ with $\sum_{t=1}^{N} c_t = N$.

*Method 1 (no trend):* divide each observation by the overall mean, average the ratios of like periods.

*Method 2 (centered moving average):* compute the $N$-period moving average, center it (for even $N$: average adjacent values), take ratio $D_t / \text{CMA}_t$, average like periods, normalise so the factors sum to $N$ (multiply by $N/\sum c$). Deseasonalised $= D_t / c_t$; forecast = deseasonalised forecast $\times c_t$.

**Winters' method** (triple exponential smoothing), model $D_t = (\mu + G t)\,c_t + \epsilon_t$, constants $\alpha,\beta,\gamma$:

$$S_t = \alpha \frac{D_t}{c_{t-N}} + (1-\alpha)(S_{t-1}+G_{t-1})$$
$$G_t = \beta (S_t - S_{t-1}) + (1-\beta) G_{t-1}$$
$$c_t = \gamma \frac{D_t}{S_t} + (1-\gamma) c_{t-N}$$
$$F_{t,t+\tau} = (S_t + \tau G_t)\, c_{t+\tau-N}$$

After each update the latest $N$ factors are renormalised to sum to $N$. Initialisation (two seasons): $V_1,V_2$ = season means, $G_0 = (V_2-V_1)/N$, $S_0 = V_2 + G_0\frac{N-1}{2}$, initial factors $= D_t / (V_i + (\tfrac{N+1}{2}-j)G_0)$, averaged and normalised.

*Use:* weekday/time-of-day patterns in demand and no-show rate.

> The Winters recursions are written in their standard form; the slide equations did not extract from the PowerPoint (images/equation objects). Verify against FT05 slides 35–36.

## 8. Box–Jenkins / ARIMA (FT06)

Backshift operator: $B D_t = D_{t-1}$. Differencing: $\nabla D_t = D_t - D_{t-1}$, $\nabla^2 D_t = D_t - 2D_{t-1} + D_{t-2}$, seasonal $\nabla_s D_t = D_t - D_{t-s}$.

| Model | Equation |
|---|---|
| AR($p$) | $D_t = a_0 + a_1 D_{t-1} + \dots + a_p D_{t-p} + \epsilon_t$ |
| MA($q$) | $D_t = b_0 - b_1\epsilon_{t-1} - \dots - b_q\epsilon_{t-q} + \epsilon_t$ |
| ARMA(1,1) | $D_t = c + a_1 D_{t-1} - b_1\epsilon_{t-1} + \epsilon_t$ |
| ARIMA($p,d,q$) | $\Phi_p(B)\nabla^d D_t = c + \Theta_q(B)\epsilon_t$ |
| Seasonal ARIMA | $\Phi_p(B)\Lambda_P(B^s)\nabla^d\nabla_s^D D_t = \Theta_q(B)\Gamma_Q(B^s)\epsilon_t$ |

Useful facts: AR(1) needs $\lvert a_1\rvert<1$, $\rho_j = a_1^j$, mean $\mu = a_0/(1-a_1-\dots-a_p)$; MA(1): $\rho_1 = -b_1/(1+b_1^2)$, $\rho_k=0$ for $k\ge 2$. AR order is read from the PACF, MA order from the ACF. Workflow: transform → identify → estimate → forecast → check residuals (zero mean, normal, Ljung–Box).

*Use:* optional; only if the project forecasts daily demand as a time series.

## Not covered by the course

The slides cover time-series forecasting. They contain **no** logistic regression, random forest, AUC, calibration, overbooking or queueing formulas; those are listed in [`overbooking.md`](overbooking.md) from standard references and must be checked against the project's own sources.
