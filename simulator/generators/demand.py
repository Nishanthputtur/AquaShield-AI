"""Demand generation — deliberately deferred.

The reviewed AquaShield AI requirements do not define a separate
demand-generation feature. The SRS specifies virtual sensor
measurement, controlled simulation, and abnormal-condition analysis.
It does not specify a demand model, demand forecasting, demand-driven
sensor behaviour, or upstream/downstream propagation based on demand.

Because of that, this module remains a documented stub. Implementing
demand generation here would introduce behaviour that is not part of
the approved requirements.

What this module must NOT do until a documented requirement exists:

    - Define a demand class, model, or forecast.
    - Modify or generate sensor readings.
    - Influence sensor ranges, event severity, or simulation ticks.
    - Introduce upstream/downstream propagation between assets.
    - Import sensor, event, analytics, backend, or frontend modules.
    - Register or activate any event.
    - Perform work at import time.

If a future requirement document explicitly defines a demand-related
feature with its own inputs, outputs, and acceptance tests, this file
is the intended place for it. Until then, keep it empty of behaviour.

Scope boundary for the simulator:

    city/        what assets exist
    sensors/     normal readings
    events/      abnormal conditions
    generators/  orchestration and lifecycle (this package)
    analytics/   interpretation and scoring (outside the simulator)

Demand generation, if ever added, would belong in this package and
would still be subject to the rule that the simulator never performs
analytics or scoring.
"""