import pytest
from pydantic import ValidationError

from app.schemas.api_key import ApiKeyCreate


def test_api_key_create_trims_name():
    payload = ApiKeyCreate(name="  Reporting script  ")

    assert payload.name == "Reporting script"


def test_api_key_create_rejects_blank_name():
    with pytest.raises(ValidationError):
        ApiKeyCreate(name="   ")
