"""
Utilitários de segurança para mascaramento de segredos.
"""

def mask_key(key: str, show_chars: int = 4) -> str:
    """
    Mascara uma chave/segredo para logging seguro.
    
    Args:
        key: Chave a ser mascarada
        show_chars: Número de caracteres a mostrar no final
    
    Returns:
        Chave mascarada
    
    Exemplo:
        >>> mask_key("sk-proj-1234567890abcdef")
        "sk-****cdef"
    """
    if not key or len(key) <= show_chars:
        return "****"
    
    prefix_len = min(6, len(key) // 3)
    return f"{key[:prefix_len]}****{key[-show_chars:]}"


def mask_url(url: str) -> str:
    """
    Mascara credenciais em URL para logging seguro.
    
    Args:
        url: URL a ser mascarada
    
    Returns:
        URL mascarada
    
    Exemplo:
        >>> mask_url("postgresql://user:pass@host:5432/db")
        "postgresql://user:****@host:5432/db"
    """
    if not url or '://' not in url:
        return "****"
    
    try:
        parts = url.split('://')
        dialect = parts[0]
        
        if '@' in parts[1]:
            credentials, rest = parts[1].split('@', 1)
            if ':' in credentials:
                user = credentials.split(':')[0]
                masked_credentials = f"{user}:****"
            else:
                masked_credentials = "****"
            
            return f"{dialect}://{masked_credentials}@{rest}"
        else:
            return url
    except Exception:
        return "****"
