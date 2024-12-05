import asyncio
from homeassistant.components.cover import CoverEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.components.cover import CoverEntityFeature

class MeibesServoDrive(CoverEntity):
    def __init__(self, name: str, switch_plus: str, switch_minus: str, position_entity: str = 0, max_time_to_move: int = 30):
        """Initialize the servo drive."""
        self._name = name
        self._switch_plus = switch_plus  # Switch activation function
        self._switch_minus = switch_minus  # Switch deactivation function
        self._position = 0  # Initial position of the servo drive (0 - closed)
        self._target_position = 0  # Target position
        self._is_moving = False  # Movement status
        self._max_time_to_move = max_time_to_move  # Maximum time for movement (in seconds)
        self._position_entity = position_entity

    @property
    def name(self):
        return self._name

    @property
    def current_cover_position(self):
        """Returns the current position of the servo drive from 0 to 100."""
        """Get current position from input_number state."""
        state = self.hass.states.get(self._position_entity)
        if state:
            self._position = int(float(state.state))
        return self._position

    @property
    def is_open(self):
        """Checks if the servo drive is open (position > 0)."""
        return self._position > 0

    @property
    def is_closed(self):
        """Checks if the servo drive is closed (position 0)."""
        return self._position == 0

    @property
    def is_moving(self):
        """Returns the movement status."""
        return self._is_moving

    @property
    def supported_features(self):
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION | CoverEntityFeature.STOP

    async def async_open_cover(self):
        """Open the servo drive (to position 100)."""
        if not self._is_moving:
            self._target_position = 100
            await self._move_servo()

    async def async_close_cover(self):
        """Close the servo drive (to position 0)."""
        if not self._is_moving:
            self._target_position = 0
            await self._move_servo()

    async def async_set_cover_position(self, position):
        """Set the position of the servo drive from 0 to 100."""
        self._target_position = max(0, min(100, position))  # Limit the value between 0 and 100
        await self._move_servo()

    async def async_stop_cover(self):
        if self._is_moving:
            if self.hass.states.is_state(self._switch_minus, "on"):
                await self._toggle_switch_state(self._switch_minus, "off")
            elif self.hass.states.is_state(self._switch_plus, "on"):
                await self._toggle_switch_state(self._switch_plus, "off")
            self._position = self._target_position
            self.is_moving = False
        self.schedule_update_ha_state()

    async def async_reset_position(self):
        """Reset the servo drive position in case of desynchronization."""
        self._is_moving = True
        await self._toggle_switch_state(self._switch_plus, "on")
        # Wait for the movement to complete
        await asyncio.sleep(self._max_time_to_move)
        # Turn off swith
        await self._toggle_switch_state(self._switch_plus, "off")
        self._is_moving = False
        self._position = 100
        self._target_position = 50
        await self._move_servo()

    async def _move_servo(self):
        """Move the servo to the target position using time delays."""
        if self._target_position == self._position:
            self._is_moving = False
            return  # Already in the target position, no need to move

        self._is_moving = True
        movement_time = abs(self._target_position - self._position) * self._max_time_to_move / 100  # Calculate movement time

        if self._target_position > self._position:
            # Move towards opening
            await self._toggle_switch_state(self._switch_plus, "on")
        else:
            # Move towards closing
            await self._toggle_switch_state(self._switch_minus, "on")

        # Wait for the movement to complete
        await asyncio.sleep(movement_time)

        # After movement, check the final position
        self._position = self._target_position
        self._is_moving = False

        # Turn off switch once movement is completed
        if self.hass.states.is_state(self._switch_minus, "on"):
            await self._toggle_switch_state(self._switch_minus, "off")
        else:
            await self._toggle_switch_state(self._switch_plus, "off")
        self.schedule_update_ha_state()
        await self._save_position()


    async def _toggle_switch_state(self, switch_entity_id: str, state: str):
        """Toggle the state of the switch."""
        """Turn the switch on or off."""
        if state == "on":
            await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": switch_entity_id})
        elif state == "off":
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_entity_id})

    async def _save_position(self):
        """Save the current position of the servo to input_number."""
        await self.hass.services.async_call(
            "input_number",
            "set_value",
            {"entity_id": self._position_entity, "value": self._position},
        )


async def async_setup_platform(
    hass: HomeAssistant, config: dict, async_add_entities: AddEntitiesCallback, discovery_info=None
):
    """Setup the platform for integrating with the servo drive."""
    switch_plus = config.get("switch_plus")  # Get switch plus from configuration.yaml
    switch_minus = config.get("switch_minus")  # Get switch minus from configuration.yaml
    max_time_to_move = config.get("max_time_to_move")  # Get max_time_to_move from configuration.yaml
    name = config.get("name", "Meibes Servo Drive")  # Default name if not provided
    position_entity = config.get("position_entity", "input_number.meibes_servo_position")  #Get entity that keeps current position

    # Check that both switches are defined
    if switch_plus is None or switch_minus is None:
        raise ValueError("Both 'switch_plus' and 'switch_minus' must be defined in the configuration.")

    # Create the servo drive entity
    servo_drive = MeibesServoDrive(name, switch_plus, switch_minus, position_entity, max_time_to_move)

    # Add entity to Home Assistant
    async_add_entities([servo_drive])

    # Registering services (e.g., open_servo_drive, close_servo_drive, set_servo_drive_position)
    async def open_servo_drive(call):
        """Open the servo drive."""
        await servo_drive.async_open_cover()

    async def close_servo_drive(call):
        """Close the servo drive."""
        await servo_drive.async_close_cover()

    async def set_servo_drive_position(call):
        """Set the position of the servo drive."""
        position = call.data.get("position")
        await servo_drive.async_set_cover_position(position)

    async def reset_position(call):
        await servo_drive.async_reset_position()

    hass.services.async_register("meibes_servo", "open_servo_drive", open_servo_drive)
    hass.services.async_register("meibes_servo", "close_servo_drive", close_servo_drive)
    hass.services.async_register("meibes_servo", "set_servo_drive_position", set_servo_drive_position)
    hass.services.async_register("meibes_servo", "reset_servo_drive_position", reset_position)
