# Système de Gestion de Tournois

Application web développée avec Django permettant la gestion complète de tournois sportifs.

## Fonctionnalités

- 🏆 Gestion des tournois (création, modification, suppression)
- 👥 Gestion des équipes et des participants
- 📊 Suivi des matchs et des statistiques
- 👮 Gestion des organisateurs et responsables
- 📧 Système de notifications

## Prérequis

- Python 3.8+
- Django 4.0+
- Autres dépendances listées dans requirements.txt

## Installation

1. Cloner le dépôt
   ```
   git clone https://github.com/MohamedLemine1x/Gestion_tournoi.git
   cd Gestion_tournoi
   ```

2. Créer un environnement virtuel
   ```
   python -m venv .venv
   source .venv/bin/activate  # Sur Windows: .venv\Scripts\activate
   ```

3. Installer les dépendances
   ```
   pip install -r requirements.txt
   ```

4. Appliquer les migrations
   ```
   python manage.py migrate
   ```

5. Lancer le serveur de développement
   ```
   python manage.py runserver
   ```

## Structure du Projet

Le projet est organisé en plusieurs applications Django :
- `tournois` : Gestion des informations des tournois
- `equipes` : Gestion des équipes
- `participants` : Gestion des participants
- `matchs` : Gestion des matchs et résultats
- `statistiques` : Analyses et statistiques des tournois
- `notifications` : Système de notifications
- `accounts` : Gestion des utilisateurs
- `organisateurs` : Gestion des organisateurs
- `responsables` : Gestion des responsables

## Contribution

Les contributions sont les bienvenues ! Veuillez consulter les issues ouvertes ou en créer de nouvelles pour discuter des fonctionnalités souhaitées.

## Licence

[MIT License](LICENSE) 