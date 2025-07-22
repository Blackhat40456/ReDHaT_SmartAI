from waitress import serve
from panel import app
from threading import Thread
import os, socket, time

try: PORT = int(os.environ.get('PORT'))
except: PORT = 8000

t = Thread(target=serve, kwargs=dict(app=app, port=PORT), daemon=True)
t.start()

while 1:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        if s.connect_ex(('127.0.0.1', PORT)) == 0: break
    time.sleep(1)

print('Server running on port', PORT, flush=True)

if __name__ == '__main__':
    try: t.join()
    except KeyboardInterrupt: pass

