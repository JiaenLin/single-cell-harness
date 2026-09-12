# Blind conversions

The maker's only honest evidence that it generalises is a tool it has never seen, converted by an
agent that has never seen the maker. Everything else — the overfit scan, the held-out eight, the
ladder — is what can be read off a family while that evidence is unspent (`docs/DEVELOPING.md`
§11). A blind conversion spends it, once per tool, and this directory is where each one is
recorded: **predictions written before the run, results written after, and the cost.**

```
NNNN-<tool>.md
```

Numbered, never renumbered. A record is not a job script and not a post-mortem: the job script
(`jobs/blind_convert.pbs`) is how a cluster-side blind test runs, and a post-mortem is about a
defect that escaped. A record here is about **the maker's generality, measured**, and it carries
three things a post-mortem does not:

- **the predictions**, numbered, written before anything runs — a blind test whose predictions
  were written afterwards is a description;
- **the cost**, in the plugin-maker skill's own currency: maker defects found, decisions that
  needed a person, job submissions, commands run. If these do not fall from one record to the
  next, the maker is not improving and plugins are being converted by hand;
- **what the agent did without being told**, because the workflow is for agents and the record
  of one cold agent's path through it is the only measurement of that there is.

A tool converted here is test material. It lands in the target repository only as such — beside
its smoke plugins, never in its shipped set — and the round's rules (`rules:` in the target's
`DEVPOINTS.yaml`) decide whether it lands at all.
