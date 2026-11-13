"""Plain-text notification e-mails; HTML escaping would corrupt them."""
import jinja2

TEXT_TEMPLATES = jinja2.Environment(loader=jinja2.PackageLoader("svcdesk", "mail"), autoescape=False)


def render_text(name: str, context: dict) -> str:
    return TEXT_TEMPLATES.get_template(name).render(**context)
