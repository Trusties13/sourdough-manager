"""Tests for config-flow form serialisation."""
from homeassistant.helpers import selector
from voluptuous_serialize import convert

from custom_components.sourdough_manager.config_flow import _schema


def test_user_form_schema_serialises():
    """The add-integration form can be sent to the frontend."""
    converted = convert(_schema({}, True), custom_serializer=selector.selector_serializer)
    assert converted


def test_options_form_schema_serialises():
    """The Configure form can be sent to the frontend."""
    converted = convert(_schema({}, False), custom_serializer=selector.selector_serializer)
    assert converted
