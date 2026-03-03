import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings
from app.analyzers.sentiment_analyzer import generate_crisis_note
from loguru import logger
from datetime import datetime
from typing import List, Dict
import redis.asyncio as aioredis
import json


class AlertManager:
    """Gestionnaire d'alertes temps reel pour le QG de campagne Wadagni."""

    ALERT_LEVELS = {
        "CALME": {"color": "#22c55e", "emoji": "verde", "threshold_negative": 30},
        "VIGILANCE": {"color": "#f59e0b", "emoji": "jaune", "threshold_negative": 50},
        "TENSION": {"color": "#f97316", "emoji": "orange", "threshold_negative": 65},
        "CRISE": {"color": "#ef4444", "emoji": "rouge", "threshold_negative": 80},
    }

    def __init__(self):
        self.recipients = settings.alert_recipients_list
        self.crisis_keywords = settings.crisis_keywords_list

    def calculate_alert_level(self, negative_pct: float) -> str:
        """Calculer le niveau d'alerte en fonction du % negatif."""
        if negative_pct >= 80:
            return "CRISE"
        elif negative_pct >= 65:
            return "TENSION"
        elif negative_pct >= 50:
            return "VIGILANCE"
        else:
            return "CALME"

    def detect_crisis_keywords(self, content: str) -> List[str]:
        """Detecter les mots cles de crise dans un contenu."""
        found = []
        content_lower = content.lower()
        for keyword in self.crisis_keywords:
            if keyword.lower() in content_lower:
                found.append(keyword)
        return found

    def detect_volume_spike(self, current_count: int, avg_count: float) -> bool:
        """Detecter un pic de volume anormal."""
        multiplier = settings.ALERT_VOLUME_SPIKE_MULTIPLIER
        return current_count > (avg_count * multiplier) and avg_count > 0

    async def send_email_alert(
        self,
        subject: str,
        body: str,
        alert_level: str = "VIGILANCE",
        recipients: List[str] = None,
    ) -> bool:
        """Envoyer une alerte par email au QG de campagne."""
        try:
            if not recipients:
                recipients = self.recipients

            if not recipients or not settings.SMTP_USER:
                logger.warning("Alerte email: pas de destinataires configures")
                return False

            level_info = self.ALERT_LEVELS.get(alert_level, self.ALERT_LEVELS["VIGILANCE"])
            color = level_info["color"]

            html_body = f"""
            <html><body>
            <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                <div style="background: {color}; color: white; padding: 15px; border-radius: 8px 8px 0 0;">
                    <h2>ALERTE RW MONITOR - {alert_level}</h2>
                    <p>{datetime.now().strftime('%d/%m/%Y %H:%M')} WAT</p>
                </div>
                <div style="padding: 20px; border: 1px solid #e5e7eb;">
                    <pre style="white-space: pre-wrap; font-family: Arial; font-size: 14px;">{body}</pre>
                </div>
                <div style="padding: 10px; background: #f3f4f6; font-size: 11px; color: #6b7280;">
                    RW Social Monitor - Confidentiel - QG Campagne Wadagni 2026
                </div>
            </div>
            </body></html>
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = f"[RW MONITOR - {alert_level}] {subject}"
            message["From"] = settings.SMTP_USER
            message["To"] = ", ".join(recipients)
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=False,
                start_tls=True,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)

            logger.info(f"Alerte email envoyee: {subject} -> {recipients}")
            return True

        except Exception as e:
            logger.error(f"Erreur envoi alerte email: {e}")
            return False

    async def trigger_crisis_alert(self, crisis_mentions: List[Dict], crisis_type: str) -> None:
        """Declencher une alerte de crise complete."""
        logger.warning(f"ALERTE CRISE: {crisis_type} - {len(crisis_mentions)} mentions")

        # Generer la note de crise avec l'IA
        crisis_note = await generate_crisis_note(crisis_mentions, crisis_type)

        # Envoyer l'email
        await self.send_email_alert(
            subject=f"CRISE DETECTEE: {crisis_type}",
            body=crisis_note,
            alert_level="CRISE",
        )

    async def trigger_volume_spike_alert(self, current: int, average: float) -> None:
        """Declencher une alerte de pic de volume."""
        body = f"""PIC DE MENTIONS DETECTE

Mentions actuelles: {current}
Moyenne habituelle: {average:.0f}
Ratio: x{current/average:.1f}

Verifier immediatement les sources et l'origine du pic."""

        await self.send_email_alert(
            subject=f"Pic de mentions: {current} mentions (x{current/average:.1f} la normale)",
            body=body,
            alert_level="TENSION",
        )


alert_manager = AlertManager()
