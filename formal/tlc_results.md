# TLC Model-Check Results

**Status:** PENDING — TLC has not yet been run on this specification.

## Command

```
java -jar tla2tools.jar -config formal/TLCConfig.cfg formal/freedom_kernel.tla 2>&1 | tee formal/tlc_results.txt
```

## Configuration

Create `formal/TLCConfig.cfg` with the content in that file.

## Next step

Install TLC from https://github.com/tlaplus/tlaplus/releases and run the command above.
Document the result (pass or counterexample) by updating this file with:
- Timestamp of run
- Exact output from TLC
- If counterexample found: the invariant violated and the fix applied

## Known limitations

The TLA+ spec at `formal/freedom_kernel.tla` has stated invariants but has not been
mechanically verified. This file will be updated once TLC is run.

Last reviewed: 2026-05-16. TLC model-check PENDING.
