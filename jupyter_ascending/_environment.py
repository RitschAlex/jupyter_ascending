import os

EXECUTE_HOST = os.getenv("JUPYTER_ASCENDING_EXECUTE_HOST", "localhost")
EXECUTE_PORT = os.getenv("JUPYTER_ASCENDING_EXECUTE_PORT", 8888)

EXECUTE_HOST_LOCATION = (EXECUTE_HOST, EXECUTE_PORT)
EXECUTE_HOST_URL = f"http://{EXECUTE_HOST_LOCATION[0]}:{EXECUTE_HOST_LOCATION[1]}/jupyter_ascending"

LOG_LEVEL = os.getenv("JUPYTER_ASCENDING_LOG_LEVEL", "INFO")
SHOW_TO_STDOUT = os.getenv("JUPYTER_ASCENDING_SHOW_TO_STDOUT", False)

# Flag to force the classic Notebook UI / nbclassic codepath (use when running nbclassic or Notebook 6).
USE_NBCLASSIC = os.getenv("JUPYTER_ASCENDING_CLASSIC") == "1"
# TODO: it would be great for this to be an environment variable... but unfortunately we need to know the value
#  on the javascript side as well, and I'm not sure how to get this value over there easily. Would love help!
SYNC_EXTENSION = "sync"
