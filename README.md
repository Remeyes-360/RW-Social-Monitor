# RW Social Monitor

> Plateforme de veille et monitoring des reseaux sociaux pour Romuald Wadagni - Election presidentielle Benin 2026

## Architecture

```
rw-social-monitor/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── collectors/   # Collecteurs multi-plateformes
│   │   ├── analyzers/    # Moteur IA analyse sentiment
│   │   ├── models/       # Modeles base de donnees
│   │   ├── api/          # Routes API REST
│   │   └── alerts/       # Systeme alertes temps reel
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # Next.js dashboard
│   ├── src/
│   │   ├── components/   # Composants UI
│   │   ├── pages/        # Pages dashboard
│   │   └── hooks/        # Hooks React
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Plateformes monitorees

- Facebook (posts, commentaires, groupes publics)
- X / Twitter (tweets, mentions, hashtags)
- Instagram (posts publics, reels, stories)
- TikTok (videos, commentaires)
- YouTube (videos, commentaires)
- Telegram (canaux publics, supergroups)
- WhatsApp Channels (canaux publics)
- Presse en ligne beninoise

## KPIs Suivis

1. Volume de mentions Wadagni par plateforme/jour
2. Sentiment (positif/neutre/negatif)
3. Co-mentions Wadagni + Talon
4. Top narratifs pro/anti/hesitants
5. Top comptes/canaux moteurs
6. Alertes rumeurs et crises

## Stack Technique

- **Backend**: Python 3.11, FastAPI, Celery
- **Frontend**: Next.js 14, TailwindCSS, Recharts
- **Base de donnees**: PostgreSQL + Redis
- **IA**: OpenAI GPT-4 + analyse sentiment custom
- **Deploiement**: Docker + Docker Compose

## Demarrage rapide

```bash
# Cloner le repo
git clone https://github.com/Remeyes-360/RW-Social-Monitor.git
cd RW-Social-Monitor

# Configurer les variables d'environnement
cp .env.example .env
# Editer .env avec vos cles API

# Lancer avec Docker
docker-compose up -d

# Acceder au dashboard
open http://localhost:3000
```

## Livrables War Room

- Brief quotidien "Meteo numerique Wadagni" (1 page)
- Note de crise (declenchee automatiquement sur pic negatif)
- Note hebdomadaire strategique

---
*RW Social Monitor - Outil confidentiel de veille strategique*
