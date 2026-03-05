
import traceback
from worker import Fetcher, Middleware

# We wrap the application import in a try/except block.
# This is the most crucial change.
try:
    # This is the standard import of our Flask app.
    # If this fails, the `except` block will be executed.
    from app import app as flask_app
    
    # If the import is successful, we create the fetcher from the app.
    app = Fetcher.from_app(flask_app)
    
    # We also store a flag to know that the import was successful.
    APP_ERROR = None

except Exception:
    # If ANY exception occurs during the import of `app.py` 
    # (e.g., database connection error, syntax error, etc.),
    # we catch it here.
    
    # We store the full error traceback in the APP_ERROR variable.
    APP_ERROR = traceback.format_exc()
    
    # We set the `app` to None, so we know it failed to load.
    app = None

# The middleware remains the same.
middleware = Middleware()

@middleware.function
def fetch(request):
  # When a request comes in, we first check if the app failed to load.
  if APP_ERROR:
    # If `APP_ERROR` is not None, it means our app crashed on startup.
    # Instead of showing "Hello World" or a generic error, we return a 
    # response containing the actual error message.
    # This gives us direct feedback on what went wrong inside `app.py`.
    return Response(f"Failed to initialize Flask app:\n{APP_ERROR}", status=500)
  
  # If the app loaded correctly (APP_ERROR is None), we proceed as normal,
  # passing the request to the Flask app.
  if app:
    return app.fetch(request)
  
  # A final fallback in case something unexpected happens.
  return Response("Application could not be loaded and no error was captured.", status=500)

