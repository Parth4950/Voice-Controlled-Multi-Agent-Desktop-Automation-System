import json
import os
import re

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_key(key):
    cleaned = (key or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def remember(key, value):
    data = load_memory()
    norm_key = normalize_key(key)
    if not norm_key:
        return None
    previous = data.get(norm_key)
    data[norm_key] = value.strip()
    save_memory(data)
    return previous


def recall(key):
    data = load_memory()
    norm_key = normalize_key(key)
    if not norm_key:
        return None
    if norm_key in data:
        return data[norm_key]

    # small fuzzy fallback for "favorite color" vs "fav color"
    query_tokens = set(norm_key.split())
    for stored_key, stored_value in data.items():
        if norm_key in stored_key or stored_key in norm_key:
            return stored_value
        stored_tokens = set(stored_key.split())
        if query_tokens and stored_tokens and query_tokens.intersection(stored_tokens):
            return stored_value
    return None
