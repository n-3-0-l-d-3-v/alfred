"""The mentor: everything that decides *what the learner is allowed to see*.

The AC gate is enforced in two independent layers so a bug in one doesn't leak
a solution:

1. Schema layer (`contracts`): the pre-AC response model has no field capable
   of carrying code, and a validator rejects code-shaped strings anyway.
2. Serving layer (`service`): checks `session.solved` before opening levels 5+
   or any approach code, and cards are validated code-free at load time.
"""
