"""A stand-in for scIntegrate's package, for tests that drive `int@scintegrate` through `sch` without
scanpy, anndata, harmonypy or scIB. Run as scIntegrate is: `python -m scintegrate.cli`, with this
directory's parent on PYTHONPATH. See cli.py, which carries the stand-in's version: a second version
string here would be a second version of the harness to its own consistency check (conform S6)."""
