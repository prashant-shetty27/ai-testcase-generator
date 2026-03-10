import random
from datetime import datetime

QUOTES = [
    "Be Smart. Be Realistic.",
    "Stay focused and keep moving forward.",
    "Success is built on consistency.",
    "Think big, act small.",
    "Every day is a new opportunity.",
    "Challenge yourself, grow stronger.",
    "Progress, not perfection.",
    "Lead with purpose and passion.",
    "Keep learning, keep improving.",
    "Make it happen, today."
]

def get_daily_quote():
    # Change quote every 24 hours based on date
    day_seed = datetime.utcnow().strftime('%Y-%m-%d')
    idx = hash(day_seed) % len(QUOTES)
    return QUOTES[idx]
