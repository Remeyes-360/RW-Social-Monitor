from openai import AsyncOpenAI
from app.config import settings
from loguru import logger
from typing import Optional
import json

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

NARRATIFS_WADAGNI = [
    "dauphin_talon", "candidat_impose", "candidat_elites", "continuity",
    "rupture", "competence_eco", "bilan_ministere_finances", "corruption",
    "CRIET", "jeunesse_chomage", "wadagni_2026", "troisieme_mandat_deguise",
    "homme_paris", "reformes_positives",
]

SYSTEM_PROMPT = """
Tu es un analyste politique specialise dans la politique beninoise.
Ta tache est d'analyser des mentions sur les reseaux sociaux concernant Romuald Wadagni,
candidature potentielle a la presidentielle du Benin 2026.

Pour chaque contenu analyse, tu dois retourner un JSON avec:
- sentiment: 'positif', 'neutre', 'negatif', ou 'crise'
- sentiment_score: float entre -1.0 (tres negatif) et 1.0 (tres positif)
- narratifs: liste des narratifs detectes parmi: dauphin_talon, candidat_impose, candidat_elites, continuity, rupture, competence_eco, bilan_ministere_finances, corruption, CRIET, jeunesse_chomage, wadagni_2026, troisieme_mandat_deguise, homme_paris, reformes_positives
- keywords: top 5 mots cles politiques
- is_talon_comention: bool - mention explicite de Talon en lien avec Wadagni
- comentions: liste des personnalites politiques co-mentionnees
- is_rumor: bool - contenu non verifie ou rumeur
- is_crisis: bool - contenu qui necessite une reponse urgente de la campagne
- crisis_keywords_found: liste des mots crise detectes
- summary_fr: resume en 1-2 phrases en francais pour le brief du QG
- recommended_action: 'ignorer', 'surveiller', 'repondre', 'escalader'

Reponds UNIQUEMENT avec du JSON valide, sans commentaires.
"""

_FALLBACK = {
    "sentiment": "neutre",
    "sentiment_score": 0.0,
    "narratifs": [],
    "keywords": [],
    "comentions": [],
    "is_talon_comention": False,
    "is_rumor": False,
    "is_crisis": False,
    "crisis_keywords_found": [],
    "summary_fr": "Analyse non disponible",
    "recommended_action": "surveiller",
}


async def analyze_mention(content: str, platform: str) -> dict:
    """Analyser une mention avec GPT-4."""
    try:
        prompt = f"Plateforme: {platform}\n\nContenu a analyser:\n{content}\n\nAnalyse ce contenu concernant Romuald Wadagni et retourne le JSON demande."
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        result = json.loads(response.choices[0].message.content)
        logger.debug(f"Analyse IA reussie: sentiment={result.get('sentiment')}")
        return result
    except Exception as e:
        logger.error(f"Erreur analyse IA: {e}")
        return _FALLBACK.copy()


async def generate_daily_brief(mentions_data: list) -> str:
    """Generer le brief quotidien pour le QG de campagne."""
    try:
        data_str = json.dumps(mentions_data, ensure_ascii=False)
        prompt = f"""
Voici les donnees de mentions du jour pour Romuald Wadagni:
{data_str}

Genere un brief politique concis (max 500 mots) structure comme suit:
1. INDICE METEO NUMERIQUE: (Calme/Vigilance/Tension/Crise)
2. CHIFFRES CLES DU JOUR:
3. TOP 3 NARRATIFS DU JOUR:
4. SIGNAUX FAIBLES:
5. RECOMMANDATIONS IMMEDIATES:

Ton: professionnel, factuel, actionnable pour l'etat-major de campagne."""

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un conseiller strategique pour la campagne presidentielle de Romuald Wadagni au Benin 2026."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur generation brief: {e}")
        return "Erreur lors de la generation du brief quotidien."


# FIX: Added generate_weekly_report — was imported in tasks.py but missing from this module
async def generate_weekly_report(mentions_data: list) -> str:
    """Generer le rapport strategique hebdomadaire pour le QG de campagne."""
    try:
        data_str = json.dumps(mentions_data, ensure_ascii=False)
        prompt = f"""
Voici les donnees de mentions de la semaine pour Romuald Wadagni:
{data_str}

Genere un RAPPORT STRATEGIQUE HEBDOMADAIRE (max 800 mots) structure comme suit:
1. BILAN DE LA SEMAINE: tendance generale (progression/regression/stabilite)
2. EVOLUTION DES NARRATIFS: quels narratifs ont gagne/perdu du terrain
3. ANALYSE DES PICS: evenements ayant genere des pics de mentions
4. CARTOGRAPHIE DES ACTEURS: comptes influents pro/anti Wadagni cette semaine
5. COMPARAISON SEMAINE PRECEDENTE: delta volume, sentiment, narratifs
6. RECOMMANDATIONS STRATEGIQUES POUR LA SEMAINE SUIVANTE:
7. POINTS DE VIGILANCE:

Ton: analytique, strategique, actionnable pour l'etat-major de campagne."""

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un directeur de strategie numerique pour la campagne presidentielle de Romuald Wadagni au Benin 2026."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur generation rapport hebdomadaire: {e}")
        return "Erreur lors de la generation du rapport hebdomadaire."


async def generate_crisis_note(crisis_mentions: list, crisis_type: str) -> str:
    """Generer une note de crise pour reponse rapide."""
    try:
        data_str = json.dumps(crisis_mentions, ensure_ascii=False)
        prompt = f"""
ALERTE CRISE DETECTEE - Type: {crisis_type}

Mentions en crise:
{data_str}

Genere une NOTE DE CRISE urgente (max 400 mots) avec:
1. NATURE DE LA CRISE:
2. AMPLEUR (sources, reach estime):
3. NARRATIF PRINCIPAL:
4. TRAJECTOIRE (monte/stable/descend):
5. SCENARIOS DE REPONSE (A/B/C avec recommandation):
6. ELEMENTS DE LANGAGE PROPOSES:
7. QUI PARLE, OU, QUAND:"""

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en gestion de crise pour la campagne presidentielle de Romuald Wadagni au Benin 2026."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur generation note crise: {e}")
        return "Erreur lors de la generation de la note de crise."
