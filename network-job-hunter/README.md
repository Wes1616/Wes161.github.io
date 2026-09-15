# Network Job Hunter

Outil d'automatisation de candidatures pour la recherche d'alternance en
**Infrastructure Réseau** (Technicien Réseau, NetOps, Support SISR, etc.).

Le pipeline :

1. **JobFetcher** récupère les offres publiées dans les **7 derniers jours**
   via l'API officielle [France Travail](https://francetravail.io) (filtre
   alternance + mots-clés infra réseau).
2. **AtsOptimizer** appelle l'API [Groq](https://groq.com/) (gratuite, SDK
   compatible OpenAI, modèle `llama-3.3-70b-versatile` par défaut) pour
   extraire les mots-clés techniques de l'offre (BGP, OSPF, VLAN, Ansible...),
   calculer un score de correspondance avec le profil, et réordonner/reformuler
   les puces du CV en mettant en avant les compétences pertinentes — sans
   jamais inventer d'expérience absente du profil de base.
3. **DocGenerator** génère un CV **100% compatible ATS** : une seule colonne,
   aucun tableau, aucune zone de texte, police standard — au format `.docx`
   puis converti en `.pdf` via LibreOffice.
4. **MailDispatcher** envoie la candidature par email avec le CV en pièce
   jointe.
5. **Tracker** enregistre chaque candidature dans une base SQLite locale pour
   éviter les doublons.

## Installation

```bash
cd network-job-hunter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis remplir les identifiants
```

La clé `GROQ_API_KEY` est gratuite : créer une clé sur la
[console Groq](https://console.groq.com/keys).

Dépendances système : [LibreOffice](https://www.libreoffice.org/) (commande
`soffice`) pour la conversion DOCX → PDF. Sous Windows/Mac sans LibreOffice,
utiliser `docx2pdf` à la place (nécessite Microsoft Word installé).

> **Note** : dans certains environnements sandboxés/conteneurs très restreints,
> `soffice --headless` peut échouer silencieusement ("source file could not be
> loaded") même sur un `.docx` valide, faute d'accès à des ressources système
> qu'il attend (D-Bus, `/dev/shm`, polices...). `DocGenerator.convert_to_pdf`
> détecte ce cas et lève une erreur explicite plutôt que d'échouer en
> silence. Sur un poste de travail normal (Linux/Mac/Windows avec LibreOffice
> installé normalement), la conversion fonctionne sans configuration
> particulière.

## Configuration du profil

Éditer `data/profile.yaml` avec tes informations réelles (coordonnées,
formation, compétences, expériences). Le fichier fourni est pré-rempli avec
le profil BTS SIO SISR de base ; les champs à compléter sont marqués
`# TODO`.

## Utilisation

```bash
# Mode simulation : ne fetch rien, n'envoie aucun email, ne modifie pas la DB
python -m src.main run --dry-run

# Exécution réelle (envoie les candidatures)
python -m src.main run
```

## Tests

```bash
pytest tests/
python scripts/verify_docx_ats.py   # génère un CV exemple + rapport de conformité ATS
```

## Architecture

```
config/settings.py       Configuration (.env) et constantes du domaine réseau
src/models.py            Dataclasses JobOffer, CandidateProfile, ApplicationRecord
src/job_sources/         Interface JobSource + adaptateur France Travail
src/job_fetcher.py       Agrégation, filtre 7 jours + domaine, dédoublonnage
src/ats_optimizer.py     Optimisation ATS via l'API Groq
src/doc_generator.py     Génération CV .docx -> .pdf compatible ATS
src/mail_dispatcher.py   Envoi de la candidature par email
src/tracker.py           Suivi SQLite des candidatures envoyées
src/main.py              Orchestration CLI du pipeline complet
```
