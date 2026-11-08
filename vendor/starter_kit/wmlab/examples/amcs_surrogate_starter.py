"""AMCS project starter: learn a world model (one-step predictor) from simulation
data, then VERIFY it using physical laws rather than loss alone.

System: undamped harmonic oscillator (c = 0); energy should be conserved.
Compare two models:
  (A) linear regression — matches the structure of the linear system
  (B) MLP 2-64-64-2 (pure NumPy, Adam) — a black-box model
Both achieve a low one-step loss. The project question is: during long rollouts,
which model still respects energy conservation and oscillation phase?
Run: python examples/amcs_surrogate_starter.py
"""
import numpy as np

from wmlab.sims import oscillator

rng = np.random.default_rng(0)
P = {"m": 1.0, "c": 0.0, "k": 4.0, "F0": 0.0, "w": 0.0}
DT = 0.05

# 1) Generate data: many short trajectories, pairs (s_t, s_{t+1}).
X, Yn = [], []
for _ in range(200):
    init = {"x0": rng.uniform(-1, 1), "v0": rng.uniform(-2, 2)}
    _, S = oscillator.simulate(P, init, [0, 2.0], DT)
    X.append(S[:-1]); Yn.append(S[1:])
X, Yn = np.concatenate(X), np.concatenate(Yn)

# 2A) Linear regression s_{t+1} = A s_t.
A = np.linalg.lstsq(X, Yn, rcond=None)[0].T

# 2B) MLP predicts the residual s_{t+1} - s_t.
def init_layer(i, o):
    return rng.normal(0, np.sqrt(1 / i), (i, o)), np.zeros(o)

W = [init_layer(2, 64), init_layer(64, 64), init_layer(64, 2)]
m_ = [[np.zeros_like(w), np.zeros_like(b)] for w, b in W]
v_ = [[np.zeros_like(w), np.zeros_like(b)] for w, b in W]

def forward(x):
    hs = [x]
    for i, (w, b) in enumerate(W):
        x = x @ w + b
        if i < len(W) - 1:
            x = np.tanh(x)
        hs.append(x)
    return x, hs

target = Yn - X
lr, b1, b2 = 1e-3, 0.9, 0.999
for step in range(1, 4001):
    idx = rng.integers(0, len(X), 256)
    out, hs = forward(X[idx])
    g = 2 * (out - target[idx]) / len(idx)
    for i in reversed(range(len(W))):
        w, b = W[i]
        gw, gb = hs[i].T @ g, g.sum(0)
        if i > 0:
            g = (g @ w.T) * (1 - hs[i] ** 2)
        for j, gr in enumerate((gw, gb)):
            m_[i][j] = b1 * m_[i][j] + (1 - b1) * gr
            v_[i][j] = b2 * v_[i][j] + (1 - b2) * gr ** 2
            mh, vh = m_[i][j] / (1 - b1 ** step), v_[i][j] / (1 - b2 ** step)
            upd = lr * mh / (np.sqrt(vh) + 1e-8)
            W[i] = (W[i][0] - upd, W[i][1]) if j == 0 else (W[i][0], W[i][1] - upd)
mse_mlp = np.mean((forward(X)[0] - target) ** 2)
mse_lin = np.mean((X @ A.T - Yn) ** 2)

# 3) Physics verification: long rollout from a new initial condition.
init = {"x0": 0.8, "v0": 0.0}
n = 2000  # 100 seconds, approximately 32 cycles.
_, truth = oscillator.simulate(P, init, [0, n * DT], DT)
s_lin = np.empty((n + 1, 2)); s_mlp = np.empty((n + 1, 2))
s_lin[0] = s_mlp[0] = truth[0]
for i in range(n):
    s_lin[i + 1] = A @ s_lin[i]
    s_mlp[i + 1] = s_mlp[i] + forward(s_mlp[i][None])[0][0]

E = lambda S: oscillator.energy(P, S)
for name, S, mse in [("Linear", s_lin, mse_lin), ("MLP", s_mlp, mse_mlp)]:
    drift = np.abs(E(S) - E(truth)[0]).max() / E(truth)[0]
    err = np.abs(S - truth).max()
    print(f"{name:<11} one-step loss={mse:.2e} | energy drift after 100 s={drift:.2%} | maximum trajectory error={err:.3f}")
print("\nProject suggestion: add constraints (Hamiltonian networks, symplectic integration, energy penalties),"
      " then repeat the same verification. Report physical metrics, not just loss.")
