"""Shared fixtures for the kernel tests. Everything synthetic; nothing names a project."""
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sch.kernel import Stack  # noqa: E402
from sch.plugin.test import table_fixture  # noqa: E402

PLUGINS = ROOT / "plugins"


def _chmod_own(p, mode) -> None:
    """chmod the path itself, NEVER what a link names (see `release_tree`); best effort, as a clean-up is."""
    if os.path.islink(p):
        return
    try:
        if os.chmod in os.supports_follow_symlinks:     # macOS: lchmod; elsewhere the islink above is the guard
            os.chmod(p, mode, follow_symlinks=False)
        else:
            os.chmod(p, mode)
    except OSError:
        pass


def read_only(paths) -> None:
    """Make each of `paths` read-only (0444), as delivered data are; a symlink among them is skipped, never followed:
    what it names is not the test's own file."""
    for p in paths:
        _chmod_own(p, 0o444)


def release_tree(root) -> None:
    """THE CLEAN-UP OF A TEST'S TEMP TREE (harness W056 fix 1): every directory made 0755 and every file 0644 so the
    tree can be removed, then removed. A SYMLINK IS NEVER FOLLOWED - not chmodded, not walked into - BY
    CONSTRUCTION: on 2026-11-12 a clean-up that chmodded every path it walked (`Path.chmod` follows links) set mode
    0644 on about 395 real programs a test had linked into its tree from the PATH. Only the tree's own entries change
    mode; `shutil.rmtree` then unlinks a link without touching what it names."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return
    todo = [str(root)]
    while todo:
        d = todo.pop()
        _chmod_own(d, 0o755)                        # before listing it: a 0444 directory cannot be walked
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                todo.append(e.path)
            else:
                _chmod_own(e.path, 0o644)
    shutil.rmtree(root, ignore_errors=True)


def fresh_stack(n=200, plugin_paths=None):
    tmp = Path(tempfile.mkdtemp(prefix="sch-test-"))
    rows, design = table_fixture(tmp, n=n)
    st = Stack.init(tmp / "stack", "table/1.0", str(rows), str(design),
                    keys={"value": "score", "group": "arm", "unit": "unit"},
                    plugin_paths=[str(p) for p in (plugin_paths or [])])
    return st, tmp


def write_plugin(root: Path, name: str, manifest: dict, run_py: str, extra: dict = None) -> Path:
    """A throwaway plugin directory. `manifest` is merged over a valid method manifest."""
    from sch import yamlish
    base = {"contract": "1.0", "profile": "table/1.0", "name": name, "version": "0.0.1",
            "summary": "a test plugin", "when_to_use": "in tests", "class": "method",
            "layer": "stack", "reversible": True, "state_version": 1, "inject": ["dataset"],
            "needs": [], "provides": [], "sees": [], "language": "python", "entry": "run.py",
            "needs_env": False,
            "no_runtime_invariant": "the output is a pure transformation of the declared input and nothing observable changes between calls",
            "cannot_show": ["a test plugin shows nothing"]}
    base.update(manifest)
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    yamlish.dump(base, d / "plugin.yml")
    (d / "run.py").write_text(textwrap.dedent(run_py))
    (d / "README.md").write_text("# t\n\n## What it does\nA test plugin that exists to exercise one rule of the kernel and nothing else.\n\n"
                                 "## Report surface\nWhatever numbers the test records; none of them are quotable outside the test.\n\n"
                                 "## Cost\nMilliseconds to run, nothing to unmount beyond its own contribution.\n\n"
                                 "## Known limitations\nIt is a test fixture and has never been run on real data of any kind.\n")
    for fname, content in (extra or {}).items():
        (d / fname).write_text(textwrap.dedent(content))
    return d


PROTO_HEAD = '''
import importlib.util, os, sys, json
spec = importlib.util.spec_from_file_location("protocol", os.environ["SCH_PROTOCOL"])
protocol = importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)
run = protocol.Run.from_argv()
'''


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------- a cohort as libraries
FIXTURES = Path(__file__).resolve().parent / "fixtures"

try:
    import h5py  # noqa: F401
    HAVE_H5PY = True
except ImportError:
    HAVE_H5PY = False


def write_part(path: Path, barcodes: list) -> Path:
    """One library's droplets: an .h5ad whose obs index is `barcodes`, written with h5py alone.
    The kernel reads identities through h5py and never the matrix, so no matrix is written."""
    import h5py
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        obs = f.create_group("obs")
        obs.attrs["_index"] = "_index"
        obs.create_dataset("_index", data=[b.encode() for b in barcodes])
    return path


def delivery(root: Path, tag: str, libraries: int = 3, droplets: int = 12, extra: dict = None) -> Path:
    """A delivery `root/tag/` whose manifest names its parts RELATIVE to itself, as a vendor's
    folder does - so a `latest -> tag` symlink above it re-points the whole delivery at once.
    `extra` adds barcodes to a library ({library index: [barcodes]}). Read-only, as delivered.
    Returns the manifest."""
    d = Path(root) / tag
    lines = ["sample\tassay\tambient_h5\tambient_tool\tambient_version\tambient_params\tambient_produced_by"]
    for i in range(libraries):
        bcs = [f"BC{j:05d}-1" for j in range(droplets)] + list((extra or {}).get(i, []))
        write_part(d / "libs" / f"L{i + 1}.h5ad", bcs).chmod(0o444)
        lines.append(f"L{i + 1}\tsnrna\tlibs/L{i + 1}.h5ad\tCellBender\t0.3.0\tdefaults\ta core facility")
    sheet = d / "sheet.tsv"
    sheet.write_text("\n".join(lines) + "\n")
    sheet.chmod(0o444)
    return sheet


def repoint(link: Path, target: str):
    """Re-point a symlink atomically, as an upstream rerun re-points its `latest`."""
    tmp = link.with_name(link.name + ".new")
    os.symlink(target, tmp)
    os.replace(tmp, link)


def library_cohort(dest: Path, libraries: int = 4, droplets: int = 120, assay: str = "snrna",
                   delimiter: str = "\t") -> tuple:
    """A samplesheet of `libraries` libraries, two arms, each part holding the SAME barcodes - as
    10x and Singleron barcodes legitimately recur across the libraries of one experiment - so an
    identity is only unique within its sample. Returns (samplesheet, registry, design)."""
    dest = Path(dest)
    samples = [f"L{i + 1}" for i in range(libraries)]
    bcs = [f"BC{j:05d}-1" for j in range(droplets)]
    header = ["sample", "platform", "species", "reference", "assay", "ambient_h5", "ambient_tool", "ambient_version",
              "ambient_params", "ambient_produced_by", "condition"]
    lines = [delimiter.join(header)]
    for i, s in enumerate(samples):
        part = write_part(dest / "objects" / f"{s}_ambient.h5ad", bcs)
        lines.append(delimiter.join([s, "vendor_x", "species_x", "species_x/ref_1", assay,
                                     str(part), "CellBender", "0.3.0", "defaults", "a core facility",
                                     "control" if i % 2 == 0 else "treated"]))
    sheet = dest / "samplesheet.tsv"
    sheet.write_text("# a samplesheet as a QC tool reads it\n" + "\n".join(lines) + "\n")
    # DELIVERED DATA ARE IMMUTABLE (LAYOUT: data/ is never written): read-only, as a mount demands
    # of every observation file a plugin is handed (ARCHITECTURE E2; harness W010).
    read_only([sheet] + sorted((dest / "objects").glob("*.h5ad")))
    registry = dest / "registry.tsv"
    registry.write_text("species\tbuild\tpath\nspecies_x\tref_1\treferences/species_x/ref_1\n")
    design = dest / "design.csv"
    design.write_text("sample,condition\n" + "".join(
        f"{s},{'control' if i % 2 == 0 else 'treated'}\n" for i, s in enumerate(samples)))
    return sheet, registry, design
