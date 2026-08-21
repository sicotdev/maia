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
    "skill_manage": "Je modifie un skill",
    "skill_view": "J'utilise un skill",
    "skills_list": "Je regarde la liste des skills",
    "terminal": "J'exécute une commande système",
    "todo": "Je mets à jour ma liste de tâches",
    "vision_analyze": "J'analyse une image",
    "web_extract": "Je récupère du contenu sur internet",
    "web_search": "Je fais une recherche sur le web",
    "write_file": "J'écris dans le fichier",
}


def get_tool_description(tool_name: str, args: str):
    tool_description = TOOL_DESCRIPTIONS.get(tool_name) or ""
    if tool_name == "read_file" or tool_name == "write_file" or tool_name == "patch":
        jsonObj = json.loads(args)
        path = jsonObj.get("path")
        if path:
            tool_description += f" {path}"
    return tool_description
