# Span-locked extension — review notes

Branch: `span-locked-extension` (off `master`).

Status: changes are **uncommitted** in the working tree per the
overnight constraint "Branches and uncommitted work only". Review with:

```
cd ~/projects/tei-mcp
git diff
```

## Files added / modified

- `src/tei_mcp/span_locked.py` — new module. `SpanStore` class with
  `get_source` / `tag_span` / `list_tags` / `reset` / `compose`.
- `src/tei_mcp/server.py` — modified. Adds `SpanStore` to lifespan
  context and registers five new MCP tools: `get_source`, `tag_span`,
  `compose`, `list_tags`, `reset_tags`.
- `tests/test_span_locked.py` — new. 20 tests covering happy path,
  error cases, nested tags, zero-width tags, attribute handling,
  crossing detection, and round-trip invariant.

## Test outcome

```
20 passed in 0.02s        (test_span_locked.py)
237 passed in 1.36s       (full suite, no regressions)
```

## Design notes for review

1. **Source loading is from disk.** The server reads source plaintext
   from `TEI_MCP_SPAN_SOURCE_ROOT/<id>.txt`. For Study 4 we'd point
   that at `~/projects/strutz-pilot/paper/cavriana/data/input/` for
   Cavriana letters, or to a similar directory for Bordeaux truncations.
   Setting the env var requires server restart.

2. **In-memory state.** Tags are kept in a process-local dict; they
   do not survive server restart. This is fine for a half-day pilot;
   if we want session-resumable workflows later, persist to JSON.

3. **Crossing detection.** `compose()` raises if any two tags cross
   (which is invalid XML). The check runs both up front and again
   during the linear sweep — slightly redundant, but the second check
   is essentially free.

4. **Body-text invariant.** `compose()` verifies that the rendered
   TEI's flat text content equals the source plaintext byte-for-byte.
   If it doesn't, `RuntimeError` is raised. This is the load-bearing
   invariant the paper claims for span-locked composition.

5. **`element_path` is mostly informational.** Only the LAST segment
   becomes the element local name. The rest is recorded for provenance
   and is available via `list_tags`. The full-path semantics could be
   used later to enforce schema-valid nesting at `tag_span` time
   (validating that `body/div/p/persName` is an admissible path), but
   tonight we just record it.

6. **No customisation integration yet.** The composer does not check
   that the tag is admissible per the loaded ODD customisation. This
   is the next iteration: integrate with `validator.py`'s
   `validate_element` per tag_span call so the model is told if the
   tag would violate the schema BEFORE compose() time. Out of scope
   for tonight.

## Open question for the user

Should `compose()` automatically wrap the result in the standard TEI
envelope (`<TEI><teiHeader>...</teiHeader><text><body>...</body></text></TEI>`)
or keep the current behaviour of returning just the `<body>` fragment?
The current minimal output is suitable for the Task B scoring code in
`scoring.py`, which expects body-only fragments. A full envelope mode
could be a separate flag.

## How to merge after review

```
cd ~/projects/tei-mcp
git add -p src/tei_mcp/span_locked.py src/tei_mcp/server.py tests/test_span_locked.py
git commit -m "Add span-locked composition tools"
git checkout master
git merge --no-ff span-locked-extension
git push origin master
```

Or, if you prefer to keep the branch as a PR for record:

```
git push -u origin span-locked-extension
gh pr create --base master --head span-locked-extension --title "Span-locked composition tools" --body "..."
```

(The user's existing GitHub workflow on this repo is unknown to me;
adjust as appropriate.)
