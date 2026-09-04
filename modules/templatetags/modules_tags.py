from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='divide')
def divide(value, arg):
    """Divides value by arg safely."""
    try:
        val = float(value)
        divisor = float(arg)
        if divisor == 0:
            return 0
        return val / divisor
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Returns value from dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key) or dictionary.get(str(key))
    return None

