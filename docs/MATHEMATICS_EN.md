# Mathematics and verification rationale

## 2. Mathematical model and reference solutions

### 2.1. First-order system formulation

The state vector is y(t) = [h(t), v(t), m(t)]. This representation allows all three numerical methods to use the same right-hand-side function f(t, y). The function returns the rate of change of the state, not the state at the next time step.

The burnout time follows from the mass law:

```text
t_b = (m_0 - m_f) / q
m(t) = m_0 - q·t         for 0 ≤ t ≤ t_b
m(t) = m_f               for t > t_b
```

For the baseline configuration, t_b = (1 − 0.6)/0.2 = 2 s. During powered flight, thrust is T = q·v_e = 100 N. The governing equations are:

```text
h' = v
v' = q·v_e/m - g - c·v·|v|/m
m' = -q
```

After burnout:

```text
h' = v
v' = -g - c·v·|v|/m_f
m' = 0
```

The term v·|v| preserves the direction of drag. During ascent, v ≥ 0, so v·|v| = v². At t = 0 under the baseline initial conditions, acceleration is 100/1 − 9.81 = 90.19 m/s². The initial right-hand side is therefore [0, 90.19, −0.2].

### 2.2. Analytical solution without drag

Set c = 0 and substitute m(t) = m_0 − qt into the velocity equation.

Integrating v' = q·v_e/(m_0 − qt) − g from 0 to t gives a thrust contribution of v_e·ln[m_0/(m_0 − qt)]. Integrating v(t) then gives h(t). The substitution u = m_0 − qt reduces the logarithmic integral to the form u·ln(u) − u. Integration constants are determined by h(0) = h_0 and v(0) = v_0. The resulting expressions are:

```text
v(t) = v_0 + v_e·ln(m_0 / m(t)) - g·t
h(t) = h_0 + v_0·t
       + (v_e/q)·[m_0 - m(t) - m(t)·ln(m_0/m(t))]
       - g·t²/2
```

These expressions apply during the burn. Evaluating them at t = t_b gives h_b and v_b. During coast, let τ = t − t_b:

```text
h(t) = h_b + v_b·τ - g·τ²/2
v(t) = v_b - g·τ
m(t) = m_f
τ_apogee = v_b/g
h_apogee = h_b + v_b²/(2g)
t_apogee = t_b + v_b/g
```

The solution checks the events and provides h, v and m at every exported time. In rocket/analytic.py, log1p improves logarithm evaluation when its argument would otherwise be close to 1. When x = qt/m_0 is very small, x + (1−x)ln(1−x) is evaluated using the sum xⁿ/[n(n−1)] for n from 2 to 8. This reduces cancellation between nearly equal numbers. It is a numerical evaluation of the same analytical expression.

### 2.3. Independent numerical reference with drag

For c > 0, verification/independent.py calls SciPy's solve_ivp with DOP853 and rtol = atol = 2×10⁻¹². The reference solves for h and v, while mass is evaluated algebraically from the piecewise linear mass law. Burn and coast are integrated separately. The initial coast state comes from the reference solution's own burn endpoint.

This module does not call rocket.rhs or the simulator's Euler, Heun or RK4 implementations. That separation reduces the risk that both sides of a comparison repeat the same implementation error. DOP853 is nevertheless a numerical reference with finite error, not an exact solution. The verification tolerances are much larger than the numerical error expected from this reference calculation.

The coast phase with drag and constant mass also has an analytical relation. With k = c/m_f:

```text
Δh_coast = ln(1 + k·v_b²/g) / (2k)
Δt_coast = atan(v_b·sqrt(k/g)) / sqrt(gk)
```

If h_b and v_b are taken from the simulated trajectory, this relation checks coast propagation only. It cannot establish that the preceding burn phase was correct.

## 3. Numerical algorithms and event handling

### 3.1. Euler, Heun and RK4

The integration steps are implemented in rocket/methods.py. Each function receives f, t, y and dt and returns an updated state vector. The simulator manages the time loop.

| Method | Idea behind one step | Evaluations of f | Expected global order |
|---|---|---:|---:|
| Euler | Use the derivative at the start of the step | 1 | 1 |
| Heun | Predict with Euler, then average two derivatives | 2 | 2 |
| RK4 | Combine four evaluations at the start, midpoint and end | 4 | 4 |

With Δt denoting the current step size, the formulas are:

```text
Euler:
    y_next = y + Δt·f(t, y)

Heun:
    k1 = f(t, y)
    k2 = f(t + Δt, y + Δt·k1)
    y_next = y + Δt·(k1 + k2)/2

RK4:
    k1 = f(t, y)
    k2 = f(t + Δt/2, y + Δt·k1/2)
    k3 = f(t + Δt/2, y + Δt·k2/2)
    k4 = f(t + Δt, y + Δt·k3)
    y_next = y + Δt·(k1 + 2k2 + 2k3 + k4)/6
```

For example, Euler with dt = 0.02 s and the baseline initial state gives h = 0 m, v = 1.8038 m/s and m = 0.996 kg after its first step. Altitude is still zero because Euler uses the initial velocity, which is zero. This is a property of the approximation; it does not mean that the physical rocket remains stationary for the entire first 0.02 s. Heun and RK4 use additional evaluations within the step and represent the increasing velocity more accurately.

### 3.2. Burnout: ending a step at the equation switch

Thrust changes from q·v_e to zero at t_b. If an RK4 step crosses this point without special handling, its intermediate stages may mix the two phases and reduce accuracy.

In rocket/simulator.py, a step whose proposed endpoint t + dt reaches or exceeds t_b is shortened to Δt = t_b − t. Every stage in that step uses the powered equation, including the endpoint stage. The following step uses the coast equation. At burnout, mass is set to m_f only after its discrepancy has been checked against the allowed limit. This corrects roundoff at a known phase boundary.

The state variables h, v and m are continuous through burnout, but acceleration has different left and right limits. The Event object stores a_before and a_after so that the acceleration immediately before engine shutdown is not lost.

### 3.3. Apogee: locating v = 0

During coast, if a trial step produces nonpositive velocity, the simulator knows that apogee lies within that step. The _apogee_step function bisects its duration. For each trial duration, it integrates again from the same left-hand state using the selected numerical method. Bisection stops when the time interval is sufficiently small; the default event_tol is 10⁻¹² s.

This approach does not merely select the largest altitude sample or linearly interpolate between the final two samples. It keeps event handling consistent with the integration method. Error accumulated before the event remains present: a small event-location tolerance does not imply that the entire solution is accurate to 10⁻¹².

### 3.4. Error conditions that stop integration

The simulator rejects steps with nonfinite states, nonpositive intermediate mass, violations of the ascent conditions or an unphysical increase in coast velocity. It also checks the maximum number of steps and whether the time step is so small that t + Δt equals t in floating-point arithmetic. On failure, it raises NumericalError rather than presenting an incomplete trajectory as a successful result.


## Numerical details and convergence

The positive h axis points upward. T=q*ve is thrust in newtons; c has units kg/m because c*v² is a force. Propellant mass m0−mf is fixed, so changing q changes both thrust and burn duration. Immediate liftoff requires q*ve>m0*g. The interface enforces this even for v0>0 to keep the verified domain consistent. Launch-pad contact and delayed liftoff are outside scope.

For x=q*t/m0 near zero, the altitude expression contains x+(1−x)ln(1−x), which suffers cancellation. The implementation uses the sum of x^n/[n(n−1)] for n=2,...,8 when x<1e-4, and log1p for logarithms near one. Published catalogue values are checked separately with rounding tolerances 0.05 m/s, 0.05 m and 0.5 m. They are not precise enough for RK4 convergence measurements.

For upward coast with drag, k=c/mf:

```text
coast_time = atan(vb*sqrt(k/g))/sqrt(g*k)
ha - hb = log1p(k*vb*vb/g)/(2*k)
```

The k→0 limit is vb/g and vb²/(2g). If hb and vb come from the candidate simulator, these formulas check coast only. The independently written DOP853 reference is needed to check the powered drag phase too.

One-step local errors of Euler/Heun/RK4 are O(dt²), O(dt³), O(dt⁵); global errors on a fixed smooth interval are O(dt), O(dt²), O(dt⁴). Some texts divide local error by dt; their exponents differ by one, so state the convention.

For each quantity Q, E(dt)=|Q_num−Q_exact| and

```text
p_i = ln(E(dt_i)/E(dt_i+1)) / ln(dt_i/dt_i+1)
log E = log C + p log dt
```

The local fit uses 0.1, 0.05, 0.025, 0.0125 s and checks hb,vb,ha,ta. The allowed order deviation is 0.35, a project choice rather than an instructor-imposed tolerance. Errors below 32*machine_epsilon*max(1,|Q_exact|) are excluded. Fewer than three usable levels produce INCONCLUSIVE. This roundoff floor is practical, not a rigorous floating-point bound.

Apogee bisection has a 1e-12 s time tolerance; tests require |v_apogee|≤1e-8 m/s. The residual velocity is retained rather than forced to zero. Bisection cannot correct error accumulated before the event, and finite output can still be inaccurate.

## Accuracy, stability and model error

Accuracy measures closeness to the solution of the chosen equations. Convergence concerns decreasing error as dt→0. Instability is amplification of errors or disturbances, so a large error alone does not establish instability.

Within a phase, the frozen velocity linearization is λ=−2c|v|/m. With z=λdt:

```text
Euler: R = 1+z
Heun:  R = 1+z+z²/2
RK4:   R = 1+z+z²/2+z³/6+z⁴/24
```

The negative real-axis stability intervals extend to −2 for Euler/Heun and approximately −2.785 for RK4. The study reports max|R| over actual steps as a diagnostic; it is not a stability proof for the nonlinear variable-mass event problem. At c=0, λ=0 does not make every large step accurate because mass still changes. Coarse no-drag Euler primarily demonstrates global error.

The model assumes 1D ascent, constant g,c,q,ve, no wind/density variation, lift, rotation, rail or descent. Reducing dt does not remove these modeling assumptions. Without measured flight data this is verification, not experimental validation.

## Acceleration and burn-rate optimization

Coordinate acceleration is a=dv/dt. Proper acceleration is a+g=(T−c*v*|v|)/m. In no-drag coast, a=−g but a+g=0. Report max|a|/g, max a/g and max|a+g|/g separately, including both burnout limits. Within-step peaks remain sampling estimates.

With 0.4 kg propellant, the study assumes q_min=1.05*m0*g/ve and upper bounds 0.5, 1, 2 kg/s. These are numerical exploration domains, not motor specifications. It scans 65 logarithmically spaced points per domain, refines detected local peaks, compares both endpoints and cross-checks the candidate with dt/2 and DOP853. This does not prove global optimality.

For no drag and h0=v0=0, define L=ln(m0/mf), Δm=m0−mf:

```text
ha(q) = ve²*L²/(2*g) + (ve/q)*(Δm−m0*L)
```

Since m0*L>Δm, the derivative with respect to q is positive. Apogee increases toward ve²*L²/(2g) as q→infinity. Thus an upper-bound maximum is expected; there is no finite global optimum without added constraints.
