from dataclasses import dataclass, field


@dataclass
class Ad:
    id: int | None
    title: str
    url: str
    price: float | None
    price_text: str | None = None
    location: str = ""
    description: str = ""
    attributes: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        bits = [self.title, self.description, " ".join(f"{k} {v}" for k, v in self.attributes.items())]
        return " ".join(bit for bit in bits if bit)
