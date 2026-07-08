# Maia

Maia est une application web conçue pour fournir une interface distante permettant d'interagir avec une gateway Hermes. Elle permet aux utilisateurs d'envoyer des messages et d'exécuter des commandes à distance en utilisant l'API Gateway de Hermes.

## 🚀 Aperçu

Maia agit comme un pont entre les utilisateurs et le cœur du système Hermes. Grâce à une interface web intuitive, elle simplifie la gestion des agents et des tâches sans nécessiter une interaction directe en ligne de commande ou via des clients complexes.

## ✨ Fonctionnalités principales

- **Accès à distance** : Utilisez la gateway Hermes depuis n'importe quel navigateur.
- **Envoi de messages** : Interface simplifiée pour communiquer avec les agents.
- **Exécution de commandes** : Contrôle et exécution de commandes via l'API Gateway de Hermes.
- **Interface Web** : Une expérience utilisateur fluide et centralisée.

## 🛠 Technologies utilisées

- **Backend** : [FastAPI](https://fastapi.tiangolo.com/) (Python) - Un framework moderne et performant pour construire des APIs.
- **Serveur Web** : [Uvicorn](https://uvicorn.org/) - Un serveur ASGI rapide et léger pour exécuter les applications FastAPI.
- **Templates** : [Jinja2](https://jinja.palletsprojects.com/) - Pour le rendu dynamique des pages HTML.
- **Gestion des fichiers statiques** : Intégration native pour les assets CSS/JS/Images.
- **Gestion d'environnement** : `python-dotenv` pour la configuration sécurisée des variables d'environnement.

## 📋 Installation et Configuration

### Prérequis
- Python 3.11+
- `uv` (gestionnaire de paquets et d'environnements recommandé)

### Installation
1. Clonez le dépôt :
   ```bash
   git clone <votre_url_depot>
   cd maia
   ```

2. Installez les dépendances :
   ```bash
   uv sync
   ```

3. Configurez vos variables d'environnement :
   Créez un fichier `.env` à la racine du projet avec les informations nécessaires pour la connexion à votre gateway Hermes.

4. Lancez l'application :
   ```bash
   uv run maia
   ```
   L'application sera disponible sur `http://localhost:8645`.

## 🏗 Structure du projet
- `src/maia/app.py` : Point d'entrée de l'application FastAPI.
- `templates/` : Contient les fichiers HTML de l'interface.
- `static/` : Contient les fichiers CSS, JavaScript et autres assets statiques.
- `tests/` : Suite de tests pour le projet.

## 📝 Note de développement
Ce projet a été initialisé récemment. Le développement est en cours pour étendre les fonctionnalités de communication avec l'API Hermes.
