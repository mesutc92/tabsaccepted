"""SMTP e-mail delivery for matched KAP disclosures."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from html import escape

from kap_alert.config import Settings
from kap_alert.filters import Match
from kap_alert.models import Disclosure

logger = logging.getLogger(__name__)


def build_message(
    disclosures: list[tuple[Disclosure, Match]],
    settings: Settings,
) -> EmailMessage:
    if len(disclosures) == 1:
        item, match = disclosures[0]
        subject = (
            f"KAP: {item.tickers or item.company} — "
            f"{item.summary or item.subject}"
        )
    else:
        tickers = ", ".join(
            sorted({item.tickers or item.company for item, _ in disclosures})
        )
        subject = f"KAP: {len(disclosures)} pozitif bildirim ({tickers})"
    subject = " ".join(subject.split())[:180]

    rows = []
    text_blocks = []
    for item, match in disclosures:
        labels = ", ".join(match.labels) or match.reason
        rows.append(
            "<tr>"
            f"<td>{escape(item.tickers)}</td>"
            f"<td>{escape(item.company)}</td>"
            f"<td>{escape(item.publish_date)}</td>"
            f"<td>{escape(item.subject)}</td>"
            f"<td>{escape(item.summary)}</td>"
            f"<td>{escape(labels)}</td>"
            f"<td><a href=\"{escape(item.url)}\">KAP</a></td>"
            "</tr>"
        )
        body_preview = (item.body_text or "")[:700]
        text_blocks.append(
            "\n".join(
                [
                    f"Hisse: {item.tickers}",
                    f"Şirket: {item.company}",
                    f"Tarih: {item.publish_date}",
                    f"Konu: {item.subject}",
                    f"Özet: {item.summary}",
                    f"Kategori: {labels}",
                    f"Link: {item.url}",
                    f"Metin: {body_preview}",
                    "-" * 40,
                ]
            )
        )

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; font-size: 14px;">
        <p>Aşağıdaki KAP bildirimleri pozitif etki filtresine takıldı.</p>
        <table border="1" cellpadding="6" cellspacing="0"
               style="border-collapse: collapse;">
          <thead>
            <tr>
              <th>Hisse</th><th>Şirket</th><th>Yayın</th>
              <th>Konu</th><th>Özet</th><th>Kategori</th><th>Link</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </body>
    </html>
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = settings.alert_to
    message.set_content("\n\n".join(text_blocks))
    message.add_alternative(html, subtype="html")
    return message


class Mailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, disclosures: list[tuple[Disclosure, Match]]) -> None:
        if not disclosures:
            return
        message = build_message(disclosures, self.settings)
        if self.settings.dry_run or not self.settings.mail_configured:
            logger.info("DRY-RUN e-posta konusu: %s", message["Subject"])
            body = message.get_body(preferencelist=("plain",))
            print(body.get_content() if body else message["Subject"])
            return
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as smtp:
            if self.settings.smtp_starttls:
                smtp.starttls()
            if self.settings.smtp_user:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)
        logger.info(
            "E-posta gönderildi: %s -> %s (%s bildirim)",
            self.settings.smtp_from,
            self.settings.alert_to,
            len(disclosures),
        )
