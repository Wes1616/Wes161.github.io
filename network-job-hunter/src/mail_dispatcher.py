"""Envoi de la candidature par email avec le CV en pièce jointe."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from config import settings
from src.models import CandidateProfile, JobOffer, OptimizedContent


class MailDispatcher:
    def __init__(
        self,
        smtp_host: str = settings.SMTP_HOST,
        smtp_port: int = settings.SMTP_PORT,
        smtp_user: str = settings.SMTP_USER,
        smtp_password: str = settings.SMTP_PASSWORD,
        sender_name: str = settings.SENDER_NAME,
        sender_email: str = settings.SENDER_EMAIL,
        template_path: Path = settings.EMAIL_TEMPLATE_PATH,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.template_path = template_path

    def build_message(
        self,
        job: JobOffer,
        profile: CandidateProfile,
        recipient_email: str,
        pdf_path: Path,
        optimized: OptimizedContent | None = None,
    ) -> EmailMessage:
        subject, body = self._render_template(job, profile, optimized)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.sender_name} <{self.sender_email}>"
        message["To"] = recipient_email
        message.set_content(body)

        message.add_attachment(
            pdf_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )
        return message

    def send(
        self,
        job: JobOffer,
        profile: CandidateProfile,
        recipient_email: str,
        pdf_path: Path,
        optimized: OptimizedContent | None = None,
        dry_run: bool = False,
    ) -> bool:
        message = self.build_message(job, profile, recipient_email, pdf_path, optimized)

        if dry_run:
            return False

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(message)
        return True

    def _render_template(
        self,
        job: JobOffer,
        profile: CandidateProfile,
        optimized: OptimizedContent | None,
    ) -> tuple[str, str]:
        raw = self.template_path.read_text(encoding="utf-8")
        subject_line, _, body_template = raw.partition("\n\n")
        subject_template = subject_line.removeprefix("Objet : ").strip()

        formation_courante = profile.formation[0].diplome if profile.formation else ""
        matched_keywords = (
            ", ".join(optimized.matched_keywords) if optimized and optimized.matched_keywords else "réseau et infrastructure"
        )

        context = {
            "full_name": profile.full_name,
            "target_title": profile.target_title,
            "job_title": job.title,
            "company": job.company,
            "formation_courante": formation_courante,
            "matched_keywords": matched_keywords,
            "email": profile.email,
            "phone": profile.phone,
        }

        subject = subject_template.format(**context)
        body = body_template.format(**context)
        return subject, body
