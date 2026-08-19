# Attribution

This project's architecture is inspired by
[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (MIT) and the
[Cordis](https://github.com/cordiverse/cordis) plugin kernel it is built on.

`VISION.md` §17 lists exactly which ideas are borrowed, which are adapted, and which are ours.
The borrowings are **concepts and contracts, not source code** — DeepSeek Harness is
TypeScript/Node and organised around an agent loop; this is Python and organised around a dataset.

**No source from either project is currently vendored here.** If any is vendored later, its MIT
notice travels with it and is recorded in this file, naming the file, the upstream commit and the
licence — the same discipline the upstream repository applies to its own dependencies.

The two ideas most directly taken:

- **"Everything is a plugin"** — including the parts that are usually hard-coded.
- **`register()` returns the disposer** — every contribution yields the means to reverse it. This
  is the mechanism that makes a reversible analysis possible rather than merely desirable, and it
  is theirs.
