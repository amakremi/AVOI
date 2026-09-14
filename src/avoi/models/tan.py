"""Tree-Augmented Naive Bayes (TAN) and Naive Bayes evidence models with exact inference under missing evidence.

Variables: class Y in {0,1}; evidence variables O_1..O_m (discrete, fully observed in TRAINING episodes).
Structure (TAN): Chow-Liu maximum spanning tree over conditional mutual information I(O_i; O_j | Y), learned on the
training fold only; each O_i has parents {Y, O_parent(i)}. CPTs use symmetric Dirichlet(alpha) smoothing, so a
source's likelihoods P(O_a | Y, parent) ARE the learned (smoothed) reliability of that evidence source.

Inference: for each y, the likelihood of the observed evidence subset is computed by exact sum-product message passing
on the tree (unobserved variables are marginalised). Posterior P(Y|E) and predictive P(O_a|E) follow exactly.
"""
from __future__ import annotations

import numpy as np


class DiscreteBayesNet:
    """TAN if tree=True, Naive Bayes if tree=False."""

    def __init__(self, n_outcomes: list[int], alpha: float = 1.0, tree: bool = True):
        self.K = list(n_outcomes)
        self.m = len(n_outcomes)
        self.alpha = alpha
        self.tree = tree
        self._cache: dict = {}

    # ------------------------------------------------------------------ learning
    def fit(self, X: np.ndarray, y: np.ndarray) -> "DiscreteBayesNet":
        X = np.asarray(X, dtype=int)
        y = np.asarray(y, dtype=int)
        a = self.alpha
        n1 = y.sum()
        self.prior = np.array([(len(y) - n1 + a), (n1 + a)], dtype=float)
        self.prior /= self.prior.sum()
        m, K = self.m, self.K
        self.parent = [-1] * m
        if self.tree and m > 1:
            cmi = np.zeros((m, m))
            for i in range(m):
                for j in range(i + 1, m):
                    cmi[i, j] = cmi[j, i] = self._cond_mutual_info(X[:, i], X[:, j], y, K[i], K[j])
            # Prim's maximum spanning tree rooted at the variable most informative about Y
            mi_y = [self._mutual_info(X[:, i], y, K[i]) for i in range(m)]
            root = int(np.argmax(mi_y))
            in_tree = {root}
            while len(in_tree) < m:
                best = (-1.0, None, None)
                for i in in_tree:
                    for j in range(m):
                        if j not in in_tree and cmi[i, j] > best[0]:
                            best = (cmi[i, j], i, j)
                self.parent[best[2]] = best[1]
                in_tree.add(best[2])
            self.root = root
        else:
            self.root = 0
        self.children = [[] for _ in range(m)]
        for i, p in enumerate(self.parent):
            if p >= 0:
                self.children[p].append(i)
        # CPTs: cpt[i] shape (2, K_parent or 1, K_i)
        self.cpt = []
        for i in range(m):
            p = self.parent[i]
            kp = K[p] if p >= 0 else 1
            t = np.full((2, kp, K[i]), a, dtype=float)
            pv = X[:, p] if p >= 0 else np.zeros(len(y), dtype=int)
            np.add.at(t, (y, pv, X[:, i]), 1.0)
            t /= t.sum(axis=2, keepdims=True)
            self.cpt.append(t)
        # post-order for message passing
        order, stack = [], [self.root] + [i for i in range(m) if self.parent[i] < 0 and i != self.root]
        roots = list(stack)
        visited = []
        for r in roots:
            st = [r]
            while st:
                n = st.pop()
                visited.append(n)
                st.extend(self.children[n])
        self.postorder = visited[::-1]
        self.roots = roots
        self._cache = {}
        return self

    @staticmethod
    def _mutual_info(xi, y, ki):
        joint = np.zeros((2, ki)) + 1e-9
        np.add.at(joint, (y, xi), 1.0)
        joint /= joint.sum()
        py, px = joint.sum(1, keepdims=True), joint.sum(0, keepdims=True)
        return float((joint * np.log(joint / (py * px))).sum())

    @staticmethod
    def _cond_mutual_info(xi, xj, y, ki, kj):
        joint = np.zeros((2, ki, kj)) + 1e-9
        np.add.at(joint, (y, xi, xj), 1.0)
        joint /= joint.sum()
        pz = joint.sum((1, 2), keepdims=True)
        pxz = joint.sum(2, keepdims=True)
        pyz = joint.sum(1, keepdims=True)
        return float((joint * np.log(joint * pz / (pxz * pyz))).sum())

    # ------------------------------------------------------------------ inference
    def likelihood(self, evidence: tuple) -> np.ndarray:
        """evidence: sorted tuple of (var, value). Returns [P(E|Y=0), P(E|Y=1)]."""
        hit = self._cache.get(evidence)
        if hit is not None:
            return hit
        obs = dict(evidence)
        if not self.tree:
            lik = np.ones(2)
            for i, v in obs.items():
                lik *= self.cpt[i][:, 0, v]
        else:
            msgs: dict[int, np.ndarray] = {}
            lik = np.ones(2)
            for n in self.postorder:
                # local factor over x_n: shape (2, K_n)
                local = np.ones((2, self.K[n]))
                if n in obs:
                    mask = np.zeros(self.K[n])
                    mask[obs[n]] = 1.0
                    local = local * mask
                for c in self.children[n]:
                    local = local * msgs[c]
                p = self.parent[n]
                if p >= 0:
                    # m_n(x_p) = sum_{x_n} P(x_n | y, x_p) * local(x_n) -> shape (2, K_p)
                    msgs[n] = np.einsum("ypk,yk->yp", self.cpt[n], local)
                else:
                    lik = lik * np.einsum("yk,yk->y", self.cpt[n][:, 0, :], local)
        if len(self._cache) < 500_000:
            self._cache[evidence] = lik
        return lik

    def posterior(self, evidence: tuple) -> float:
        lik = self.likelihood(evidence) * self.prior
        return float(lik[1] / lik.sum())

    def predictive(self, evidence: tuple, var: int) -> np.ndarray:
        """P(O_var = o | E) for all o, and the corresponding posteriors P(Y=1 | E, O_var=o)."""
        base = float((self.likelihood(evidence) * self.prior).sum())
        probs, posts = np.zeros(self.K[var]), np.zeros(self.K[var])
        for o in range(self.K[var]):
            ev = tuple(sorted(evidence + ((var, o),)))
            lj = self.likelihood(ev) * self.prior
            s = lj.sum()
            probs[o] = s / base
            posts[o] = lj[1] / s if s > 0 else 0.5
        probs /= probs.sum()
        return probs, posts

    def describe(self) -> dict:
        return {"type": "TAN" if self.tree else "NaiveBayes", "alpha": self.alpha, "parent": self.parent,
                "prior_satisfied": float(self.prior[1])}


class FixedReliabilityModel(DiscreteBayesNet):
    """Ablation 'without learned reliability': evidence likelihoods are NOT learned per source.

    Each outcome's nominal polarity (supports_satisfied / supports_violated / neutral, from the objective config)
    is mapped to a likelihood with ONE global reliability rho (estimated on the training fold as the pooled
    agreement rate between non-neutral nominal readings and Y). Naive-Bayes factorisation, learned class prior.
    """

    def __init__(self, n_outcomes, polarity: list[list[int]], alpha: float = 1.0):
        super().__init__(n_outcomes, alpha=alpha, tree=False)
        self.polarity = polarity  # per var, per outcome: +1 supports satisfied, -1 supports violated, 0 neutral

    def fit(self, X, y):
        X, y = np.asarray(X, int), np.asarray(y, int)
        n1 = y.sum()
        self.prior = np.array([len(y) - n1 + 1.0, n1 + 1.0])
        self.prior /= self.prior.sum()
        agree = total = 0
        for i in range(self.m):
            pol = np.array(self.polarity[i])[X[:, i]]
            nz = pol != 0
            agree += int(((pol[nz] > 0).astype(int) == y[nz]).sum())
            total += int(nz.sum())
        self.rho = (agree + 1.0) / (total + 2.0)
        self.parent = [-1] * self.m
        self.children = [[] for _ in range(self.m)]
        self.cpt = []
        for i in range(self.m):
            pol = np.array(self.polarity[i], dtype=float)
            t = np.zeros((2, 1, self.K[i]))
            for yv in (0, 1):
                w = np.where(pol == 0, 1.0, np.where((pol > 0) == (yv == 1), self.rho, 1.0 - self.rho))
                t[yv, 0, :] = w / w.sum()
            self.cpt.append(t)
        self.postorder, self.roots, self.root = list(range(self.m)), list(range(self.m)), 0
        self._cache = {}
        return self
