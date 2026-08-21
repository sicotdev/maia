import json

TOOL_DESCRIPTIONS = {
    "browser_exec": "J'utilise le navigateur web",
    "clarify": "Je te pose une question pour préciser",
    "computer_use": "J'utilise le contrôle du bureau",
    "cronjob": "Je gère une tâche planifiée",
    "delegate_task": "Je délègue une tâche à un sous-agent",
    "memory": "J'enregistre une information en mémoire",
    "patch": "Je modifie le fichier",
    "process": "Je gère un processus en arrière-plan",
    "read_file": "Je lis le contenu du fichier",
    "search_files": "Je recherche dans les fichiers",
    "session_search": "Je recherche dans nos sessions passées",
    "skill_manage": "Je modifie le skill",
    "skill_view": "J'utilise le skill",
    "skills_list": "Je regarde la liste des skills",
    "terminal": "J'exécute la commande",
    "todo": "Je mets à jour ma liste de tâches",
    "vision_analyze": "J'analyse une image",
    "web_extract": "Je récupère du contenu sur internet",
    "web_search": "Je fais une recherche sur le web",
    "write_file": "J'écris dans le fichier",
}


def get_tool_description(tool_name: str, args: str | dict):
    tool_description = TOOL_DESCRIPTIONS.get(tool_name) or ""

    # Convert args to dict if needed
    json_obj = json.loads(args) if isinstance(args, str) else args

    if tool_name in ["read_file", "write_file", "patch"]:
        path = json_obj.get("path")
        if path:
            tool_description += f" {path}"
    elif tool_name in ["skill_view", "skill_manage"]:
        name = json_obj.get("name")
        if name:
            tool_description += f" {name}"
    elif tool_name == "terminal":
        command = json_obj.get("command")
        if command:
            tool_description += f" {command}"

    return tool_description
