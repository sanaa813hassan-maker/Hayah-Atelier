from app import app as flask_app
from worker import Fetcher, Middleware

# The fetcher makes HTTP requests to the origin.
# This is a reference to the Flask app.
app = Fetcher.from_app(flask_app)

# The middleware intercepts requests and responses.
# It can be used to add authentication, logging, etc.
# For now, we just pass the request through.
middleware = Middleware()

@middleware.function
def fetch(request):
  return app.fetch(request)