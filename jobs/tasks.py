import random
import time
import logging

logger = logging.getLogger(__name__)

def handle_send_email(payload):
    """Simulate sending an email"""
    to = payload.get('to')
    subject = payload.get('subject')

    # Simulate transient failure 50% of the time
    if random.random() < 0.5:
        raise Exception("SMTP server temporarily unavailable")

    time.sleep(2)
    logger.info(f"Email sent to {to} with subject {subject}")
    return {"message": f"Email sent to {to}", "subject": subject}

def handle_generate_report(payload):
    """Simulate generating a report"""
    report_type = payload.get('report_type', 'default')
    rows = payload.get('rows', 100)
    time.sleep(3)
    logger.info(f"Report generated: {report_type} with rows {rows}")
    return {"report_type": report_type, "rows_processed": rows, "status": "generated"}

# Registry - maps task_type string to handler function
TASK_REGISTRY = {
    "send_email": handle_send_email,
    "generate_report": handle_generate_report,
}