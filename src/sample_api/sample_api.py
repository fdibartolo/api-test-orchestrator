import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Sample API")

# In-memory "database" — initialized from seed.json and wiped on restart
seed_file = Path(__file__).with_name("seed.json")
db: dict[str, list] = json.loads(seed_file.read_text(encoding="utf-8"))
id_counters: dict[str, int] = {
    resource: max((item["id"] for item in items), default=0) + 1
    for resource, items in db.items()
}


def next_id(resource: str) -> int:
    id_ = id_counters[resource]
    id_counters[resource] += 1
    return id_


@app.get("/{resource}")
def list_items(resource: str):
    if resource not in db:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")
    return db[resource]


@app.get("/{resource}/{item_id}")
def get_item(resource: str, item_id: int):
    if resource not in db:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")
    for item in db[resource]:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.post("/{resource}", status_code=201)
def create_item(resource: str, body: dict[str, Any]):
    if resource not in db:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")
    body["id"] = next_id(resource)
    db[resource].append(body)
    return body


@app.patch("/{resource}/{item_id}")
def update_item(resource: str, item_id: int, body: dict[str, Any]):
    if resource not in db:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")
    for item in db[resource]:
        if item["id"] == item_id:
            item.update(body)
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/{resource}/{item_id}", status_code=204)
def delete_item(resource: str, item_id: int):
    if resource not in db:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")
    for i, item in enumerate(db[resource]):
        if item["id"] == item_id:
            db[resource].pop(i)
            return
    raise HTTPException(status_code=404, detail="Item not found")


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8001)
