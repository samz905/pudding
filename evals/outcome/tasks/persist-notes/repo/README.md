# notes

Tiny notes API. `PORT=8000 python3 server.py`

    curl -X POST localhost:8000/notes -d '{"text":"buy milk"}'
    curl localhost:8000/notes

Tests: `python3 -m unittest`
