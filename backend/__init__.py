"""AquaShield AI backend package.

This marker file lets the backend run as a proper package when the
application is launched from the repository root:

    uvicorn backend.app.main:app --reload

All backend imports use the `backend.app...` path.
"""