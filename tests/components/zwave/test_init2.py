"""Tests for the Z-Wave init."""
import asyncio
from collections import OrderedDict
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

import pytest
from pytz import utc
import voluptuous as vol

from homeassistant.bootstrap import async_setup_component
from homeassistant.components import zwave
from homeassistant.components.zwave import (
    CONF_DEVICE_CONFIG_GLOB,
    CONFIG_SCHEMA,
    DATA_NETWORK,
    const,
)
from homeassistant.components.zwave.binary_sensor import get_device
from homeassistant.const import ATTR_ENTITY_ID, EVENT_HOMEASSISTANT_START
from homeassistant.helpers.entity_registry import async_get_registry
from homeassistant.helpers.device_registry import async_get_registry as get_dev_reg
from homeassistant.setup import setup_component
from homeassistant.core import HomeAssistant

from tests.common import (
    async_fire_time_changed,
    get_test_home_assistant,
    mock_coro,
    mock_registry,
)
from tests.mock.zwave import MockEntityValues, MockNetwork, MockNode, MockValue


async def test_value_discovery_existing_entity(hass: HomeAssistant, mock_openzwave):
    """Test discovery of a node."""
    mock_receivers = {}

    def mock_connect(receiver, signal, *args, **kwargs):
        mock_receivers[signal] = receiver

    with patch("pydispatch.dispatcher.connect", new=mock_connect):
        await async_setup_component(hass, "zwave", {"zwave": {}})
        await hass.async_block_till_done()

    #assert len(mock_receivers) == 1

    node = MockNode(node_id=11, generic=const.GENERIC_TYPE_THERMOSTAT, specific=const.SPECIFIC_TYPE_THERMOSTAT_GENERAL_V2)

    mode = MockValue(
        data='heat',
        data_items= ['off', 'heat', 'cool', 'heat_cool'],
        node=node,
        instance=1,
        index=1,
        command_class=const.COMMAND_CLASS_THERMOSTAT_MODE,
        genre=const.GENRE_USER,
    )

    setpoint_heating = MockValue(
        label = "Heating 1",
        data=61.0,
        node=node,
        instance=1,
        index=1,
        command_class=const.COMMAND_CLASS_THERMOSTAT_SETPOINT,
        genre=const.GENRE_USER,
        units="F",
    )
    setpoint_cooling = MockValue(
        label = "Cooling 1",
        data=70.0,
        node=node,
        instance=1,
        index=2,
        command_class=const.COMMAND_CLASS_THERMOSTAT_SETPOINT,
        genre=const.GENRE_USER,
        units="F",
    )

    hass.async_add_job(mock_receivers[MockNetwork.SIGNAL_VALUE_ADDED], node, mode)
    hass.async_add_job(mock_receivers[MockNetwork.SIGNAL_VALUE_ADDED], node, setpoint_heating)
    hass.async_add_job(mock_receivers[MockNetwork.SIGNAL_VALUE_ADDED], node, setpoint_cooling)
    await hass.async_block_till_done()
    
    print(mock_receivers)
    print(hass.states.get("climate.mock_node_mock_value"))
    
    assert (
        hass.states.get("climate.mock_node_mock_value").attributes["temperature"] == 61.0
    )

    def mock_update(self):
        self.hass.add_job(self.async_update_ha_state)

    with patch.object(
        zwave.node_entity.ZWaveBaseEntity, "maybe_schedule_update", new=mock_update
    ):
        # mode = MockValue(
        #     data='heat_cool',
        #     data_items= ['off', 'heat', 'cool','heat_cool'],
        #     node=node,
        #     instance=1,
        #     index=1,
        #     command_class=const.COMMAND_CLASS_THERMOSTAT_MODE,
        #     genre=const.GENRE_USER,
        # )
        # hass.async_add_job(mock_receivers[MockNetwork.SIGNAL_VALUE_ADDED], node, mode)
        mode.data = 'heat_cool'
        mode.refresh()
        await hass.async_block_till_done()

    
    assert (
        hass.states.get("climate.mock_node_mock_value").attributes["target_temp_low"] == 61.0
    )
    assert (
        hass.states.get("climate.mock_node_mock_value").attributes["target_temp_high"] == 70.0
    )
    # assert (
    #     hass.states.get("climate.mock_node_mock_value").attributes[
    #         "current_temperature"
    #     ]
    #     == 23.5
    # )


