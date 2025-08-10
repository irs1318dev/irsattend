import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
from typing import Tuple

from . import config

def send_email(email: str, student_name: str, qr_code_path: str) -> Tuple[bool, str]:
    """
    Sends an email with a QR Code to a student.
    """

    if not all([config.SMTP_SERVER, config.SMTP_USERNAME, config.SMTP_PASSWORD]):
        missing = []
        if not config.SMTP_SERVER: missing.append("SMTP_SERVER")
        if not config.SMTP_USERNAME: missing.append("SMTP_USERNAME") 
        if not config.SMTP_PASSWORD: missing.append("SMTP_PASSWORD")
        return False, f"SMTP settings missing: {', '.join(missing)}"

    # Create email
    msg = MIMEMultipart('related')
    msg['Subject'] = "Your Attendance Pass"
    msg['From'] = f"{config.EMAIL_SENDER_NAME} <{config.SMTP_USERNAME}>"
    msg['To'] = email

    # Email using HTML, makes it look nicer
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ background: #662382; background: linear-gradient(135deg,rgba(102, 35, 130, 1) 39%, rgba(249, 178, 52, 1) 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: bold; color: #fff; }}
            .content {{ padding: 30px; background-color: #eee; text-align: center; }}
            .pass-container {{ text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; }}
            .pass-container img {{ max-width: 100%; height: auto; border: 2px solid #e9ecef; border-radius: 12px; }}
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 IRS 1318 Attendance System</h1>
                <p>Your Attendance Pass</p>
            </div>
            <div class="content">
                <h2>Hello {student_name}! 👋</h2>
                <p>Your attendance pass is ready! This pass is unique to you and will be used to track your attendance at every meeting.</p>
                <p>Please star this email or take a screenshot of your QR code for personal safekeeping.</p>

                <div class="pass-container">
                    <h3>Your Attendance Pass:</h3>
                    <img src="cid:qr_code" alt="Your personal pass">
                </div>

                <p><strong>Important:</strong> This pass is personal to you. You are not to share it with others.</p>
            </div>
            <div class="footer">
                <p>IRS 1318 Robotics Team | Attendance Management System</p>
                <p>If you have any questions, please speak with a mentor.</p>
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    # Add the image
    try:
        if not os.path.exists(qr_code_path):
            return False, f"QR Code image not found at {qr_code_path}"

        with open(qr_code_path, 'rb') as fp:
            img = MIMEImage(fp.read())
            img.add_header('Content-ID', '<qr_code>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(qr_code_path))
            msg.attach(img)
    except FileNotFoundError:
        return False, f"QR Code image not found at {qr_code_path}."
    except Exception as e:
        return False, f"Error attaching QR Code image: {str(e)}"

    # Send the email
    try:
        smtp_port = getattr(config, 'SMTP_PORT', 465)
        
        with smtplib.SMTP_SSL(config.SMTP_SERVER, smtp_port) as server:
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(msg)
            
        return True, "Email sent successfully."
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP Authentication failed: {str(e)}"
    except smtplib.SMTPServerDisconnected as e:
        return False, f"SMTP Server disconnected: {str(e)}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"