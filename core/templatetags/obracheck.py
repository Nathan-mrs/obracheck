from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def brl(valor):
    """Formata número como moeda brasileira: 1234.5 -> R$ 1.234,50"""
    try:
        valor = Decimal(valor or 0)
    except Exception:
        return valor
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@register.filter
def iniciais(usuario):
    nome = str(usuario).split()
    return "".join(p[0] for p in nome[:2]).upper()
