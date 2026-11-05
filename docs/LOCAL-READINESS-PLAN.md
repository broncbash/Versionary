# Local readiness workflow

This is a design note for an offline, disposable-only verification coordinator. It must not deploy software, change live containers, start services, enroll agents, merge branches, or configure hosted CI.

The coordinator will run local regression tests, isolated HTTPS acceptance, and the exhaustive recovery matrix. It will validate results through the existing offline evidence gate and print a summary. Operator approval remains required before any production work.
