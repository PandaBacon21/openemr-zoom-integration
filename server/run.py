# Under Gunicorn's gevent worker, gevent's monkey-patching handles pure-Python
# libraries (pymysql, requests) automatically. psycopg2 is a C extension and
# won't cooperate without an explicit patch — without this, every Postgres query
# blocks the entire worker process, defeating gevent's concurrency entirely.
# The patch is a no-op when gevent isn't active (Flask dev server, pytest).
try:
    from gevent import monkey
    if monkey.is_module_patched("socket"):
        from psycogreen.gevent import patch_psycopg
        patch_psycopg()
except ImportError:
    pass

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)