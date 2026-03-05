
from worker import Response, Middleware

middleware = Middleware()

@middleware.function
def fetch(request):
  # This is a simple test to confirm if deployments are working.
  # It removes all complexity of the Flask app.
  # If we see this message, the deployment pipeline is working.
  # If we still see "Hello World", the pipeline is broken.
  return Response("Deployment Test Succeeded. The problem is in the application code.", headers={'Content-Type': 'text/plain'})

