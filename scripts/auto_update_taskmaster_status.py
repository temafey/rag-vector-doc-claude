"""
Auto-update Taskmaster task statuses by analyzing codebase with both fuzzy and embedding-based semantic search.

Requirements:
    pip install rapidfuzz sentence-transformers torch

- Uses rapidfuzz for fuzzy keyword matching
- Uses sentence-transformers for deep semantic similarity
- If either method finds a strong match, marks the task as done in tasks/tasks.json
"""
import os
import re
import json
import ast
from pathlib import Path
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util
from typing import Any, Dict, List

TASKS_JSON = "tasks/tasks.json"
CODE_ROOT = "app"
FUZZY_THRESHOLD = 80
EMBEDDING_THRESHOLD = 0.6

model = SentenceTransformer('all-MiniLM-L6-v2')

def load_tasks() -> tuple[list[dict], dict | None]:
    with open(TASKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict) and "tasks" in data:
            return data["tasks"], data
        return data, None

def save_tasks(tasks: list[dict], parent: dict | None = None):
    # Always save as a dict with 'tasks' key for Taskmaster compatibility
    if parent is not None:
        parent["tasks"] = tasks
        with open(TASKS_JSON, "w", encoding="utf-8") as f:
            json.dump(parent, f, indent=2, ensure_ascii=False)
    else:
        # If parent is None, wrap in a dict
        with open(TASKS_JSON, "w", encoding="utf-8") as f:
            json.dump({"tasks": tasks}, f, indent=2, ensure_ascii=False)

def extract_keywords(task: Dict[str, Any]) -> List[str]:
    text = f"{task['title']} {task.get('description', '')}"
    words = re.findall(r'\b\w+\b', text.lower())
    stopwords = {"the", "and", "for", "with", "that", "will", "into", "from", "all", "are", "can", "this", "to", "of", "in", "on", "by", "a", "an", "is", "as", "at"}
    return [w for w in words if len(w) > 2 and w not in stopwords]

def fuzzy_match(a: str, b: str, threshold: int = FUZZY_THRESHOLD) -> bool:
    return fuzz.partial_ratio(a, b) >= threshold

def code_matches_keywords_fuzzy(keywords: List[str], code_path: Path) -> bool:
    with open(code_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
    try:
        tree = ast.parse(code)
    except Exception:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            name = node.name.lower()
            for k in keywords:
                if fuzzy_match(k, name):
                    if len(node.body) > 1 and not (
                        all(isinstance(stmt, ast.Pass) for stmt in node.body) or
                        any(isinstance(stmt, ast.Raise) and getattr(stmt.exc, 'id', '') == 'NotImplementedError' for stmt in node.body)
                    ):
                        return True
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            doc = node.value.s.lower()
            for k in keywords:
                if fuzzy_match(k, doc):
                    return True
    for line in code.splitlines():
        if line.strip().startswith("#"):
            for k in keywords:
                if fuzzy_match(k, line.lower()):
                    return True
    return False

def embedding_match(task_text: str, code_path: Path, threshold: float = EMBEDDING_THRESHOLD) -> bool:
    with open(code_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
    try:
        tree = ast.parse(code)
    except Exception:
        return False
    code_snippets = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            code_snippets.append(node.name)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            code_snippets.append(node.value.s)
    code_snippets += [line.strip() for line in code.splitlines() if line.strip().startswith("#")]
    if not code_snippets:
        return False
    task_emb = model.encode([task_text], convert_to_tensor=True)
    code_embs = model.encode(code_snippets, convert_to_tensor=True)
    sims = util.pytorch_cos_sim(task_emb, code_embs)[0]
    return any(sim > threshold for sim in sims)

def find_code_for_task(keywords: List[str], task_text: str, root: str = CODE_ROOT) -> List[str]:
    matches = []
    for path in Path(root).rglob("*.py"):
        if code_matches_keywords_fuzzy(keywords, path) or embedding_match(task_text, path):
            matches.append(str(path))
    return matches

def repair_tasks_json_structure():
    bak_path = TASKS_JSON + ".bak"
    if not os.path.exists(bak_path):
        print("No backup file found, skipping structure repair.")
        return
    with open(TASKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(bak_path, "r", encoding="utf-8") as f:
        bak_data = json.load(f)
    # If current is a list and backup is a dict with 'tasks', fix it
    if isinstance(data, list) and isinstance(bak_data, dict) and "tasks" in bak_data:
        print("Repairing tasks.json structure to match backup (wrapping in 'tasks' key)...")
        with open(TASKS_JSON, "w", encoding="utf-8") as f:
            json.dump({"tasks": data}, f, indent=2, ensure_ascii=False)
    else:
        print("No structure repair needed.")

def update_task_txt_status(task_id: int, status: str):
    txt_path = f"tasks/task_{task_id:03d}.txt"
    if not os.path.exists(txt_path):
        return
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Replace the main task status
    content, n = re.subn(r"(# Status: )\w+", f"\\1{status}", content, count=1)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)

def update_subtask_txt_status(task_id: int, sub_id: int, status: str):
    txt_path = f"tasks/task_{task_id:03d}.txt"
    if not os.path.exists(txt_path):
        return
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Find the subtask header and update the status line below it
    sub_header = f"## {sub_id}."
    for i, line in enumerate(lines):
        if line.strip().startswith(sub_header):
            # Look for the next line starting with '###' and containing 'Status:'
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip().startswith("### Status:"):
                    lines[j] = re.sub(r"(### Status: )\w+", f"\\1{status}", lines[j])
                    break
            break
    with open(txt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def main():
    repair_tasks_json_structure()
    tasks, parent = load_tasks()
    if parent is not None:
        tasks_list = parent["tasks"]
    else:
        tasks_list = tasks
    for i, task in enumerate(tasks_list):
        keywords = extract_keywords(task)
        task_text = f"{task['title']} {task.get('description', '')}"
        matches = find_code_for_task(keywords, task_text)
        if matches:
            shown = matches[:3]
            extra = len(matches) - 3
            msg = f"Task {task['id']} likely done (matches: {', '.join(shown)}"
            if extra > 0:
                msg += f", +{extra} more"
            msg += ")"
            print(msg)
            task["status"] = "done"
            update_task_txt_status(task["id"], "done")
        for j, sub in enumerate(task.get("subtasks", [])):
            sub_keywords = extract_keywords(sub)
            sub_text = f"{sub['title']} {sub.get('description', '')}"
            sub_matches = find_code_for_task(sub_keywords, sub_text)
            if sub_matches:
                shown = sub_matches[:3]
                extra = len(sub_matches) - 3
                msg = f"Subtask {task['id']}.{sub['id']} likely done (matches: {', '.join(shown)}"
                if extra > 0:
                    msg += f", +{extra} more"
                msg += ")"
                print(msg)
                sub["status"] = "done"
                update_subtask_txt_status(task["id"], sub["id"], "done")
    save_tasks(tasks_list, parent)

if __name__ == "__main__":
    main() 