# Whole-trajectory verification

## 6. Trajectory and dynamics-consistency verification

### 6.1. Why endpoint checks are insufficient

A trajectory may retain the correct burnout and apogee values while containing an error at an intermediate sample. For example, increasing only the velocity near t = 3 s by 25 m/s can leave the endpoint quantities unchanged. Verification must therefore inspect the trajectory history, not just a few final values.

First, trajectory_coverage checks array shapes, finite values, strictly increasing times and positive mass. It also requires a burnout observation and enough intervals in each phase. Empty or incomplete data do not receive a passing result merely because the missing region cannot be checked.

### 6.2. Comparing states at the same times

reference_history uses the time array t supplied by the trajectory under test. For c = 0, it evaluates the analytical expressions. For c > 0, it evaluates the DOP853 dense solution at those times. Two observations are not treated as equivalent simply because they have the same index on different grids.

For each quantity x, the acceptance condition at every sample is:

```text
|x_sim(t_i) - x_ref(t_i)| ≤ atol + rtol·|x_ref(t_i)|
error_ratio_i = absolute_error_i / allowed_error_i
PASS only if every error_ratio_i ≤ 1
```

| Quantity | atol | rtol |
|---|---:|---:|
| h | 0.01 m | 10⁻⁶ |
| v | 0.01 m/s | 10⁻⁶ |
| m | 10⁻¹⁰ kg | 0 |
| a, algebraic output check | 10⁻⁸ m/s² | 10⁻¹⁰ |

Each report records the maximum absolute error, maximum relative error where defined, relevant times and the error-to-tolerance ratio. Relative error is undefined when the reference is exactly zero; the absolute tolerance still provides a valid acceptance criterion. A large relative error near v = 0 does not by itself imply a large physical discrepancy.

### 6.3. Checking whether the data satisfy the ODE

For an interval [t_i, t_(i+1)] entirely within one phase, the checker compares the slope of the observations with the mean right-hand side at the endpoints. Let Δt_i = t_(i+1) − t_i:

```text
R_h = (h_(i+1) - h_i)/Δt_i - (v_i + v_(i+1))/2
R_v = (v_(i+1) - v_i)/Δt_i - (a_i^ODE + a_(i+1)^ODE)/2
R_m = (m_(i+1) - m_i)/Δt_i - m'_expected
```

During burn, m'_expected = −q; during coast, it is zero. The acceleration a^ODE is evaluated independently from the equation and observed state. The checker also compares the separately exported a channel with its corresponding algebraic acceleration.

R_h and R_v cannot be required to vanish exactly because secant differentiation and endpoint averaging introduce their own discretization error. Their tolerances combine three contributions: the same stencil's error on the independent reference, propagated input-state tolerances, and floating-point roundoff.

For example, if ε_h and ε_v are the allowed state errors at the observations, the R_h budget has the form:

```text
B_h = bias_reference
    + (ε_h,i + ε_h,i+1)/Δt_i
    + (ε_v,i + ε_v,i+1)/2
    + roundoff
```

For the velocity equation, the implementation bounds acceleration sensitivity to v and m inside the tolerance region around the reference. It uses L_v = 2c·v_high/m_low and L_m = (T + c·v_high²)/m_low². This prevents corrupted candidate samples from inflating their own acceptance tolerance.

### 6.4. Treatment of the burnout region

No differentiation interval crosses the thrust discontinuity. The burnout observation belongs to both adjacent intervals, but the left interval uses powered acceleration and the right interval uses coast acceleration. The stored a channel at burnout must use the right-hand value. This phase separation avoids false failures caused by the physically correct acceleration jump.


## Detailed error budgets

`trajectory_reference_checks(result, params=None, tolerances=None)` compares every exported time. It does not use a separate sparse comparison grid. Parameters come from agreed inputs, not candidate event states. DOP853 solves burn and coast separately with rtol=atol=2e-12 and evaluates dense output at candidate times without extrapolation. If the candidate apogee is slightly late, the reference coast is actually integrated through that final time. This continuation belongs to the verifier, not the ascent simulator.

Pointwise limits are:

| Field | Absolute tolerance | Relative tolerance |
|---|---:|---:|
| h | 0.01 m | 1e-6 |
| v | 0.01 m/s | 1e-6 |
| m | 1e-10 kg | 0 |
| algebraic a | 1e-8 m/s² | 1e-10 |

These continue the existing endpoint accuracy requirements; they are not measurement uncertainties or official course thresholds. Piecewise-linear mass needs only roundoff allowance. Method and dt metadata never relax tolerances; actual intervals come from result.t. An otherwise valid coarse method can correctly FAIL accuracy checks.

The algebraic check compares the exported a with F=(T−c*v*|v|)/m−g at the candidate state. At burnout, stored a is the coast-side value. Because a is algebraic, this check does not need a finite-difference allowance.

For a same-phase interval of length d, define:

```text
D_h = (h[i+1]−h[i])/d − (v[i]+v[i+1])/2
D_v = (v[i+1]−v[i])/d − (F[i]+F[i+1])/2
D_m = (m[i+1]−m[i])/d − (−q during burn, 0 during coast)
```

Their units are m/s, m/s² and kg/s. The h/v residuals need not vanish for exact samples because trapezoidal quadrature has O(d²) bias after division by d. Compute the identical stencil on the independent reference at the same times, giving B_h=|D_h,ref| and B_v=|D_v,ref|. Candidate mutations cannot increase this reference bias.

Let ε_h, ε_v, ε_m be pointwise state allowances. The triangle inequality gives:

```text
budget_h = B_h + (ε_h[i]+ε_h[i+1])/d
                 + (ε_v[i]+ε_v[i+1])/2 + roundoff_h
m_low = m_ref−ε_m > 0
v_high = |v_ref|+ε_v
L_v = 2*c*v_high/m_low
L_m = (T+c*v_high²)/m_low²
ε_F = L_v*ε_v + L_m*ε_m
budget_v = B_v + (ε_v[i]+ε_v[i+1])/d
                 + (ε_F[i]+ε_F[i+1])/2 + roundoff_v
budget_m = (ε_m[i]+ε_m[i+1])/d + roundoff_m
```

The RHS bounds use partial derivatives over the reference error box. Mass has no quadrature bias within either phase. Each column uses a practical roundoff allowance of `64*machine_epsilon*max(1,|reference_i|,|reference_i+1|)/d`. This is not a rigorous floating-point error theorem, and DOP853 remains a numerical reference.

Acceptance compares each residual against its own interval budget. Budgets depend on reference values, the actual grid, parameters and declared tolerances, not mutation magnitude or solver metadata. Dynamics uses reference-based stencil calibration, so it is not wholly independent of reference comparison. The ODE/algebraic checks and state-reference checks complement each other.

## Coverage and burnout

A full trajectory needs a burnout sample within 1e-10 s of tb and at least two intervals in each phase. Missing coverage, NaN/Inf, repeated/decreasing time or nonpositive mass fails `trajectory_coverage`.

The last burn interval uses powered acceleration at both ends, including the left limit at tb. The first coast interval uses coast acceleration at both ends, including the right limit. No central difference crosses the jump and no surrounding region is discarded. Nonuniform grids are supported. Extremely short intervals can enlarge derivative budgets; pointwise state and acceleration checks remain active.

## Read SeriesCheck reports

- `max_absolute_error`: largest difference with units; for dynamics this is the raw residual before removing reference stencil bias.
- `max_relative_error`: largest |error/reference| where reference is nonzero. Exact zeros are excluded and counted in `relative_undefined_count`; near-zero values can produce large ratios. Residuals with zero reference have null relative error.
- `max_error_ratio`: maximum pointwise error/budget. PASS requires every ratio≤1.
- `worst_time_s`: time of the largest ratio, or interval midpoint for derivatives; it need not be the largest-absolute-error location.
- `min_allowed_error`, `max_allowed_error`, `allowed_error_at_worst`: reveal the grid-dependent allowance.

Do not compare max(error) with max(budget) from potentially different times. The implementation compares corresponding samples/intervals.

Run `python -m verification.mutations` for `outputs/trajectory_verification.json/.csv`. Scenario JSON includes these checks automatically, and reproduction includes them in summary and report outputs.

## Mutations and detection limits

Deep copies are mutated near t=1 s (burn) or 3 s (coast): v+25 m/s, h+1 m, m+0.02 kg or a+25 m/s². Two c values produce 16 cases. Original arrays and events are preserved, and the designated checks must fail for the demonstration to pass.

| Mutation | State-reference check | Main dynamics check |
|---|---|---|
| v | trajectory_v | dynamics_v_prime |
| h | trajectory_h | dynamics_h_prime |
| m | trajectory_m | dynamics_m_prime_burn/coast |
| a | h/v/m remain unchanged and may pass | dynamics_acceleration |

Regression tests also mutate samples just before/at/after burnout, use the wrong acceleration side at burnout, and modify v while recalculating a consistently. In the last case a=RHS can pass, but trajectory_v and dynamics_v_prime must fail.

Perturbations below tolerance or between unexported times are not guaranteed to be detected. Export all steps and events, agree accuracy requirements before testing and inspect convergence. If Member B does not export independent acceleration, require that channel before claiming it was checked. The three-column wmlab interface cannot independently verify an acceleration channel reconstructed from its own h/v/m observations.
