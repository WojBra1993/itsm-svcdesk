"""Ticket lookups for the customer portal."""
from dataclasses import dataclass


@dataclass
class Ticket:
    id: str
    requester: str
    title: str


def get_ticket_for_customer(store: dict[str, Ticket], customer: str, ticket_id: str) -> Ticket:
    """The ticket a logged-in customer asked for."""
    ticket = store.get(ticket_id)
    if ticket is None:
        raise KeyError(ticket_id)
    return ticket
