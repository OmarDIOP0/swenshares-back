# SwenShares Backend 🚀

## Description
`SwenShares` Backend est la partie serveur de la plateforme SwenShares, une solution innovante de gestion des relations avec les actionnaires (SHRM) pour les entreprises privées non cotées en bourse. Il gère la logique métier, le stockage des données et expose une API RESTful.

## Fonctionnalités principales
- Gestion des actionnaires (personnes physiques et morales)
- Traitement des transactions d'actions (achat, vente, transmission)
- Workflow d'approbation à deux niveaux pour les transactions
- Génération de rapports sur l'actionnariat et les transactions
- API sécurisée pour l'interaction avec le frontend

## Technologies utilisées
- Python 3.10
- Django
- Django REST Framework
- MySQL
- Authentification à deux facteurs

## Installation 💻

### Prérequis
- Python 3.10 ou version supérieure
- pip (gestionnaire de paquets Python)
- MySQL

### Étapes d'installation

1. Clonez le dépôt :
   ```bash
   git clone https://gitlab.com/digital-performance/swensharesback.git
   cd SwenSharesBack/
   ```
2. Créez un environnement virtuel:
   ```bash
   pip install virtualenv
   virtualenv venv 

   # Avec venv: python -m venv venv

3. Activez un environnement virtuel :
   ```bash
    .\venv\Scripts\activate # Ou Sur Lunix source venv/bin/activate

   ```

4. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

5. Configurez la base de données :
   - Copiez `.env.example` en `.env`
   - Modifiez les valeurs dans le fichier `.env` pour correspondre à votre configuration MySQL locale

6. Appliquez les migrations :
   ```bash
   python manage.py migrate
   ```

## Exécution du projet

1. Lancez le serveur de développement :
   ```bash
   python manage.py runserver
   ```

2. L'API sera accessible à l'adresse : `http://localhost:8000/api/`

## Structure du projet
```
backend/
├── swenshares/         # Projet Django principal
├── shareholders/       # Application pour la gestion des actionnaires
├── transactions/       # Application pour la gestion des transactions
├── users/              # Application pour la gestion des utilisateurs
├── manage.py
└── requirements.txt
```

## API Endpoints
- `/api/shareholders/` : Opérations CRUD sur les actionnaires
- `/api/transactions/` : Gestion des transactions d'actions
- `/api/users/` : Gestion des utilisateurs et authentification

## Développement

### Création de migrations
Après modification des modèles :
```bash
python manage.py makemigrations
```

### Exécution des tests
```bash
python manage.py test
```

## Contributeurs

### Asse Badiane
 - Développeur principal.
### Omar Diop
 - Développeur principal.
### Moussa Tamba
 - Développeur principal.


## Contribution
Les contributions sont les bienvenues ! Veuillez suivre ces étapes :
1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Poussez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request ver la branche `dev`

## Licence
Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.