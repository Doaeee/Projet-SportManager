# Projet-SportManager
Gestion d'un club de sport
## SportManager (Django 4.x)

Application web de gestion d’un club sportif (membres, coachs, activités, séances, paiements) avec **Python 3** + **Django 4.x** et une base **SQLite** en développement.

### Structure du projet
- **Projet Django**: `sportmanager/`
- **App principale**: `core/`
- **Templates globaux**: `templates/`
- **Base de données SQLite (dev)**: `db_dev.sqlite3` (base finale/active)

### Lancer l’application (Windows / PowerShell)
Dans le dossier du projet:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Ensuite:
- Accueil (redirige selon rôle): `http://127.0.0.1:8000/`
- Connexion: `http://127.0.0.1:8000/login/`
- Admin Django: `http://127.0.0.1:8000/admin/`

### Comptes / rôles
Le modèle utilisateur est `core.Utilisateur` (custom user):
- champ de connexion: **`login`**
- `email`, `role` (ADMIN / COACH / MEMBRE)

Profils:
- `core.Membre` (OneToOne -> Utilisateur)
- `core.Coach` (OneToOne -> Utilisateur)

### Pages principales
Dashboards:
- Admin: `/dashboard/admin/`
- Coach: `/dashboard/coach/`
- Membre: `/dashboard/membre/`

Admin App (hors admin Django):
- Paiements: `/admin-app/paiements/`
- Activités (CRUD): `/admin-app/activites/`
- Séances (CRUD): `/admin-app/seances/`
- Comptes (création/suppression): `/admin-app/comptes/`

Membre:
- Planning: `/membre/planning/`

Coach:
- Planning: `/coach/planning/`

### Base de données (SQLite)
La base de dev est le fichier:
- `db_dev.sqlite3`
