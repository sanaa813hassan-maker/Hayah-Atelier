import traceback
# The crucial fix is adding `Response` to the import list.
from worker import Fetcher, Middleware, Response

# We wrap the application import in a try/except block.
try:
    from app import app as flask_app
    app = Fetcher.from_app(flask_app)
    APP_ERROR = None

except Exception:
    # If ANY exception occurs during the import of `app.py`, we catch it.
    APP_ERROR = traceback.format_exc()
    app = None

middleware = Middleware()

@middleware.function
def fetch(request):
  # When a request comes in, we first check if the app failed to load.
  if APP_ERROR:
    # Now, this `Response` object is correctly defined and the code will execute.
    # We will see the actual error from the database connection or any other startup problem.
    return Response(f"Failed to initialize Flask app:\n{APP_ERROR}", status=500, headers={'Content-Type': 'text/plain'})
  
  # If the app loaded correctly, we proceed as normal.
  if app:
    return app.fetch(request)
  
  # A final fallback.
  return Response("Application could not be loaded and no error was captured.", status=500, headers={'Content-Type': 'text/plain'})
