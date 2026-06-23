
### To run the server, use the following command:
```bash
    uv run uvicorn main:app --reload
```

### To initialize alembic,
```bash 
alembic init alembic 
```


### generate migration
```bash
alembic revision --autogenerate -m "<your_migration_message>"
```

### apply to DB
```bash
alembic upgrade head
```