"""Domain services for QUILL Social (PRD 29.2).

Pure, wx-free logic that the UI and adapters build on: intelligent thread
splitting, the scheduler state machine, ordered thread publishing with
pause-on-failure, catch-up grouping, composer capability checks, and search.
Each service is independently unit-tested.
"""
