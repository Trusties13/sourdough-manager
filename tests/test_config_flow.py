"""Tests for config-flow form serialisation."""

import importlib
import sys
from pathlib import Path

from homeassistant.helpers import config_validation as cv
from voluptuous_serialize import convert

sys.path.insert(0, str(Path(__file__).parents[1]))
config_flow = importlib.import_module(
    "custom_components.sourdough_manager.config_flow"
)


def test_user_form_schema_serialises():
    """The add-integration form can be sent to the frontend."""
    converted = convert(
        config_flow._schema({}, True),
        custom_serializer=cv.custom_serializer,
    )
    assert converted


def test_options_form_schema_serialises():
    """The Configure form can be sent to the frontend."""
    converted = convert(
        config_flow._schema({}, False),
        custom_serializer=cv.custom_serializer,
    )
    assert converted
