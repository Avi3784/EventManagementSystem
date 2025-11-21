from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def get(dictionary, key):
    """Gets a value from a dictionary using the key"""
    return dictionary.get(key, '')

@register.filter
@stringfilter
def full_name(value):
    """Returns full name from first and last name"""
    try:
        return f"{value.first_name} {value.last_name}"
    except AttributeError:
        return value