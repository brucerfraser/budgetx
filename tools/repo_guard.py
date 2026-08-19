#!/usr/bin/env python3
"""repo_guard — the mechanical answer to the 2026-08-19 IDE incident.

The Anvil-synced repo carries CODE AND SPECS ONLY. This guard makes the incident's
mistake impossible to repeat by accident:

  * refuses any commit/push that tracks a path under a forbidden prefix
    (scratch/, docs/evidence/, or any media/evidence file type outside the allowlist);
  * refuses any single new blob over BLOB_LIMIT bytes (allowlisted paths excepted);
  * refuses any push that would take the whole tracked tree over TREE_LIMIT bytes
    or FILE_LIMIT files.

Budgets are deliberately far below Anvil's observed ~95 MB tolerance so drift is
caught years before it matters. A refusal prints exactly what to remove.

Install (one-time per clone; already done on Bruce's Mac):
    git config core.hooksPath tools/githooks

Modes:
    repo_guard.py --staged     check what `git commit` is about to record (pre-commit)
    repo_guard.py --tree REF   check the full tracked tree at REF (pre-push checks each
                               ref being pushed; default HEAD)
"""
import subprocess, sys, fnmatch

TREE_LIMIT = 25 * 1024 * 1024      # 25 MB total tracked tree
FILE_LIMIT = 500                   # tracked files
BLOB_LIMIT = 2 * 1024 * 1024       # 2 MB per file
FORBIDDEN_PREFIXES = ('scratch/', 'docs/evidence/', '.playwright', 'node_modules/')
FORBIDDEN_GLOBS = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.zip', '*.pdf',
                   '*.xlsx', '*.pptx', '*.sqlite', '*.db')
# Paths allowed to exist despite the globs / blob limit, with their own caps.
ALLOWLIST = {
    'anvil.yaml': 5 * 1024 * 1024,
    'tests/fixtures/*.json': 3 * 1024 * 1024,
    'theme/*': BLOB_LIMIT,
}


def _run(args):
  return subprocess.run(args, capture_output=True, text=True).stdout


def _allow(path):
  for pat, cap in ALLOWLIST.items():
    if fnmatch.fnmatch(path, pat) or path == pat:
      return cap
  return None


def check(entries, label):
  """entries: iterable of (path, size). Returns a list of violation strings."""
  bad, total, count = [], 0, 0
  for path, size in entries:
    total += size
    count += 1
    cap = _allow(path)
    if any(path.startswith(p) for p in FORBIDDEN_PREFIXES):
      bad.append('FORBIDDEN PATH   %s  (evidence never enters the synced repo — 2026-08-19 incident)' % path)
      continue
    base = path.rsplit('/', 1)[-1]
    if cap is None and any(fnmatch.fnmatch(base, g) for g in FORBIDDEN_GLOBS):
      bad.append('FORBIDDEN TYPE   %s  (media/evidence file type)' % path)
      continue
    limit = cap if cap is not None else BLOB_LIMIT
    if size > limit:
      bad.append('BLOB OVER LIMIT  %s  (%.1f MB > %.1f MB)' % (path, size / 1048576.0, limit / 1048576.0))
  if total > TREE_LIMIT:
    bad.append('TREE OVER LIMIT  %s: %.1f MB tracked > %.1f MB budget' % (label, total / 1048576.0, TREE_LIMIT / 1048576.0))
  if count > FILE_LIMIT:
    bad.append('TOO MANY FILES   %s: %d tracked > %d budget' % (label, count, FILE_LIMIT))
  return bad


def tree_entries(ref):
  out = _run(['git', 'ls-tree', '-r', '-l', ref])
  for line in out.splitlines():
    meta, path = line.split('\t', 1)
    parts = meta.split()
    if len(parts) >= 4 and parts[3].isdigit():
      yield path, int(parts[3])


def staged_entries():
  paths = _run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR']).split()
  for p in paths:
    size_out = _run(['git', 'cat-file', '-s', ':' + p]).strip()
    yield p, int(size_out) if size_out.isdigit() else 0


def main():
  mode = sys.argv[1] if len(sys.argv) > 1 else '--tree'
  if mode == '--staged':
    # Staged check: violations in the staged files themselves, plus the resulting tree.
    bad = check(staged_entries(), 'staged')
    bad = [b for b in bad if not b.startswith(('TREE OVER', 'TOO MANY'))]  # sizes judged on tree
    bad += [b for b in check(tree_entries('HEAD'), 'tree@HEAD') if b.startswith(('TREE OVER', 'TOO MANY'))]
  else:
    ref = sys.argv[2] if len(sys.argv) > 2 else 'HEAD'
    bad = check(tree_entries(ref), 'tree@%s' % ref)
  if bad:
    print('repo_guard: REFUSED — the Anvil-synced repo carries code and specs only.')
    for b in bad:
      print('  ' + b)
    print('Evidence stays on disk (gitignored). See CLAUDE.md "THE SYNCED REPO CARRIES CODE ONLY".')
    return 1
  return 0


if __name__ == '__main__':
  sys.exit(main())
