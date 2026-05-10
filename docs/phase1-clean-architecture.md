# Phase 1 Clean Architecture Notes

Phase 1 introduces a testable predictor domain boundary without replacing the
existing Streamlit workflow.

## Scope

- Add `src/config/predictor_config.py`
- Add `src/domain/predictor.py`
- Keep legacy `src/predictor.py` unchanged for UI compatibility
- Add focused pytest coverage for predictor validation, determinism, config
  behavior, and logging

## Boundary

```text
pd.DataFrame
-> IPredictor.get_projection()
-> HeuristicPredictor
-> ProjectionResult
```

The predictor domain layer does not fetch data, render UI, write files, or know
about Streamlit session state.

## Extension Path

Future predictors should implement `IPredictor` and return `ProjectionResult`.
Application services can depend on `IPredictor` instead of concrete predictor
classes.
