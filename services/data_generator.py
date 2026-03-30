"""Synthetic realistic test data."""
from __future__ import annotations

import random
import string
from dataclasses import dataclass
from typing import Dict

try:
    from faker import Faker
except ImportError:
    Faker = None  # type: ignore


@dataclass
class SyntheticProfile:
    name: str
    email: str
    phone: str
    password: str


def _fallback_name() -> str:
    first = random.choice(["Alex", "Jordan", "Sam", "Riley", "Casey", "Morgan"])
    last = random.choice(["Smith", "Garcia", "Patel", "Brown", "Lee", "Nguyen"])
    return f"{first} {last}"


def _fallback_email(name: str) -> str:
    slug = "".join(c for c in name.lower().replace(" ", ".") if c.isalnum() or c == ".")
    domain = random.choice(["example.com", "mail.test", "inbox.dev"])
    return f"{slug}@{domain}"


def _fallback_phone() -> str:
    return f"+1{random.randint(2000000000, 9999999999)}"


def _fallback_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choice(chars) for _ in range(14))


def generate_batch(count: int = 12) -> Dict[str, SyntheticProfile]:
    """Multiple profiles for repeated input tests."""
    out: Dict[str, SyntheticProfile] = {}
    fk = Faker() if Faker else None
    for i in range(count):
        if fk:
            name = fk.name()
            email = fk.email()
            phone = fk.phone_number()
            password = fk.password(length=14)
        else:
            name = _fallback_name()
            email = _fallback_email(name)
            phone = _fallback_phone()
            password = _fallback_password()
        out[f"p{i}"] = SyntheticProfile(name=name, email=email, phone=phone, password=password)
    return out


def single_profile() -> SyntheticProfile:
    return generate_batch(1)["p0"]
