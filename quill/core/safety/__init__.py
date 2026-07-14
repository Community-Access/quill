"""Runtime safety controls (wx-free).

Currently: the remote feature kill switch. Signed feature advisories arrive
inside the update manifest (:mod:`quill.core.updates`); this package resolves
them for the running version, persists the locked set locally so a kill switch
survives offline and across restarts, and exposes the state the UI consults in
its feature-enable check.
"""
