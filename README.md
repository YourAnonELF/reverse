# reverse

Reverse-IP domain checker with terminal and UI tools.

## Terminal tool

```bash
python reverse_ip_checker.py --ip 8.8.8.8 --domain dns.google
```

JSON output:

```bash
python reverse_ip_checker.py --ip 8.8.8.8 --json
```

## UI tool

```bash
python reverse_ip_checker_ui.py --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser.

## Tests

```bash
python -m unittest tests/test_reverse_ip_checker.py -v
```
