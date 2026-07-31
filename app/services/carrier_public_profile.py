from pathlib import Path


LOGO_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "carrier_logos"


def missing_public_profile_fields(carrier) -> list[str]:
    fields: list[str] = []
    if not carrier.public_name:
        fields.append("public_name")
    if carrier.experience_since_year is None:
        fields.append("experience_since_year")
    if not carrier.logo_file_name:
        fields.append("logo")
    if carrier.publication_consent_at is None:
        fields.append("publication_consent")
    if not carrier.operating_regions:
        fields.append("operating_regions")
    return fields


def carrier_logo_path(file_name: str | None) -> Path | None:
    if not file_name:
        return None
    if Path(file_name).name != file_name:
        return None
    path = LOGO_DIRECTORY / file_name
    if not path.is_file():
        return None
    return path
