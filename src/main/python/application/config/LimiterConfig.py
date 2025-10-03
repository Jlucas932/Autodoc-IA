"""
Configuração de rate limiting com limites configuráveis por variáveis de ambiente.
"""
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Obter limites de variáveis de ambiente
rate_limit_per_minute = os.getenv('RATE_LIMIT_PER_MINUTE', '30')
rate_limit_per_hour = os.getenv('RATE_LIMIT_PER_HOUR', '500')
rate_limit_per_day = os.getenv('RATE_LIMIT_PER_DAY', '2000')

# Configurar limites padrão
default_limits = [
    f"{rate_limit_per_minute} per minute",
    f"{rate_limit_per_hour} per hour",
    f"{rate_limit_per_day} per day"
]

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=default_limits,
    storage_uri=os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://'),
)
