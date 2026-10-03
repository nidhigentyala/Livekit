from dataclasses import dataclass


@dataclass
class CallerData:
    name: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    verified: bool = False