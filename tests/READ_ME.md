---
title: EZID Py Test
tags: []
---

1. Set up virtual environment

```python
    python3 -m venv .test-venv
```

2. Activate virtual environment
```python
    source .test-venv/bin/activate
```

 
3. Install requirements.txt
```python
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
```


4. Set up Django settings module
```bash
    export DJANGO_SETTINGS_MODULE=settings.tests
```

5. Start mysql
```bash
    brew services start mysql
```

6. Run mysql_test_setup.sh
```bash
    shell tests/mysql_test_setup.sh
```

7. Set up file system
```bash
    mkdir -p ../download/public ../logs
```

8. Setup DB and static files
```python
    ./manage.py migrate
    ./manage.py collectstatic --no-input
```

9. Load DB fixture
```python
    ./manage.py loaddata db
```

10. Run tests
```python
    pytest --maxfail 10
```
