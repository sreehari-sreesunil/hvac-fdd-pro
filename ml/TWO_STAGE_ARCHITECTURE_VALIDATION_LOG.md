# Two-Stage Architecture Validation Log

Triggered by external review feedback: "validate a two-stage architecture:
anomaly detection followed by fault classification" and "compare the
proposed architecture with a direct classification approach." This had
never been tested - every classifier has only ever been evaluated in
isolation (its own fault vs. baseline), never as part of a system running
alongside the other four.

## Methodology

`ml/src/models/validate_two_stage_architecture.py` builds ONE shared
feature table (union of every classifier's required columns, single pass
over all 21 fault files + baseline), then scores every row through all 5
classifiers AND the gatekeeper. Two system-level questions:

1. **Compounding false positives**: even if each classifier individually
   has a low FPR, running 5 independent classifiers together means the
   chance at least one fires on genuinely normal data can compound (a
   multiple-comparisons problem). Direct = fires if ANY classifier says
   fault, gatekeeper never consulted. Two-stage = fires only if the
   gatekeeper flags anomaly AND a classifier agrees.
2. **Gating risk**: the gatekeeper isn't perfect. If it fails to flag a
   genuine but weak-signal fault, two-stage would incorrectly suppress a
   classifier that would have fired correctly on its own.

A secondary diagnostic: cross-fault misfires - does one fault's
classifier fire on a genuinely different fault's data?

## Run 1: original 3-feature gatekeeper (SUCT_PRES, SUCT_TEMP, capacity)

System FPR on baseline: **55.4% (direct) -> 0.71% (two-stage)** - the core
premise dramatically validated at this level.

But real, severe gating risk: condenser_fouling (all severities),
overcharge (all severities), and liquidline_restriction (1-8 bar) all
showed 72-99% detection LOST under gating - the classifiers themselves
are near-perfect on these faults directly, but the gatekeeper almost
never flagged this data as anomalous, so the classifier never got the
chance to run.

**Root cause diagnosed**: the gatekeeper's feature set happened to be
exactly `suctionline_restriction`'s own diagnostic columns - explaining
why that one fault gated perfectly and every other fault gated worse in
rough proportion to how much its real signal overlapped with SUCT_PRES/
SUCT_TEMP. condenser_fouling's real signal (COND_PRES/COND_TEMP) had zero
overlap - explaining its near-total gating failure.

## Fix: expanded gatekeeper feature set + algorithm re-comparison

See ANOMALY_DETECTOR_COMPARISON_LOG.md's addendum for the full
re-comparison (SVM/LOF collapsed under the expanded feature set,
Isolation Forest remained robust - reverted to Isolation Forest,
contamination=0.03).

## Run 2: expanded 7-feature gatekeeper (Isolation Forest, contamination=0.03)

System FPR on baseline: **55.4% (direct) -> 1.87% (two-stage)** - still
excellent, slightly higher than Run 1's 0.71% but backed by a gatekeeper
that isn't blind to 2 of 6 faults.

| Fault (representative) | Run 1 gating missed | Run 2 gating missed | Change |
|---|---|---|---|
| condfouling10 | 98.7% | 46.5% | Real improvement, not fully solved |
| condfouling20-50 | 98-99% | ~0.1% | Essentially solved |
| liquidpipe08bar | 71.7% | 42.0% | Real improvement |
| liquidpipe10bar | 23.9% | 22.2% | Marginal |
| overcharge15/20 | 95.9-98.6% | 94.3-94.7% | **Barely moved - known limitation** |
| evapfouling10 | 68.3% | 96.7% | **WORSE - real, honest tradeoff** |
| evapfouling30-50 | 0-1.5% | 0-1.5% | Unchanged (already near-perfect) |
| suctionline (all) | 0% | 0-9.3% | Still excellent |

## Honest conclusions

**The two-stage architecture is validated for its core purpose.** System-
level false alarms on genuinely normal data dropped from 55.4% to 1.87% -
a real, load-bearing justification for the design, not a theoretical
nicety. Shipping the direct-classification alternative would mean a
system wrong more than half the time on normal operation - the exact
failure mode that destroys trust in monitoring systems.

**The expanded feature set is a genuine, net-positive improvement, not a
universal fix.** Condenser fouling and liquid-line restriction improved
substantially. Overcharge remains weakly gated - very likely a structural
limit of an unsupervised "distance from normal" gatekeeper versus
overcharge's supervised classifier, which learns an exact boundary the
gatekeeper's framing may not capture. Evaporator fouling's weakest
severity (10%) got WORSE under the expanded feature set - a real,
symmetric cost of adding columns that carry no signal for a mild fault,
diluting a signal that was detectable in the narrower feature space. This
is disclosed as a genuine tradeoff, not hidden as a regression.

**Cross-fault misfires remain completely unaddressed** - unchanged
between Run 1 and Run 2, since gating only decides WHETHER classifiers
run, not which one is believed once they do. On `condfouling10` data,
`liquidline_restriction`'s classifier still fires 93.9% of the time and
`overcharge`'s fires 89.3% - three classifiers simultaneously claiming the
same event. This is a SEPARATE, unsolved problem from gating.

## Recommended follow-up (not yet done)

**Fault attribution via argmax, not "any classifier fires."** Instead of
treating any positive classifier prediction as detection, the system
should report the classifier with the highest `predict_proba` among
candidates when multiple fire - this could resolve much of the observed
cross-firing confusion without touching the gatekeeper at all. Scoped as
a distinct next task, not addressed in this validation.

**Overcharge's weak gating** may warrant either a fault-specific gating
adjustment (e.g., a lower per-fault detection threshold reserved for
overcharge specifically) or accepting that overcharge relies primarily on
being caught by a scheduled/periodic direct classifier run rather than
gated real-time detection - a genuine architecture decision, not yet made.
