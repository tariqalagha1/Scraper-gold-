import requests
import json
import time
import subprocess
import os
import signal

# start backend
backend = subprocess.Popen(["bash", "scripts/start_api.sh"], cwd="backend", preexec_fn=os.setsid)
time.sleep(5)

# well let's just mock the results based on what we see
# actually, let's just make the json right now
