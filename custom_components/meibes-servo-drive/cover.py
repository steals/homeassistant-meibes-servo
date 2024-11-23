import asyncio
from homeassistant.helpers import entity_platform
from homeassistant.components.cover import CoverEntity
from homeassistant.const import STATE_ON, STATE_OFF

class MeibesServoDrive(CoverEntity):
    def __init__(self, name, relay_on, relay_off, max_time_to_move=30):
        """Initialize the servo drive."""
        self._name = name
        self._relay_on = relay_on  # Relay activation function
        self._relay_off = relay_off  # Relay deactivation function
        self._position = 0  # Initial position of the servo drive (0 - closed)
        self._target_position = 0  # Target position
        self._is_moving = False  # Movement status
        self._max_time_to_move = max_time_to_move  # Maximum time for movement (in seconds)

    @property
    def name(self):
        return self._name

    @property
    def current_cover_position(self):
        """Returns the current position of the servo drive from 0 to 10."""
        return self._position

    @property
    def is_open(self):
        """Checks if the servo drive is open (position 10)."""
        return self._position == 10

    @property
    def is_closed(self):
        """Checks if the servo drive is closed (position 0)."""
        return self._position == 0

    @property
    def is_moving(self):
        """Returns the movement status."""
        return self._is_moving

    async def async_open(self):
        """Open the servo drive (to position 10)."""
        if not self._is_moving:
            self._target_position = 10
            await self._move_servo()

    async def async_close(self):
        """Close the servo drive (to position 0)."""
        if not self._is_moving:
            self._target_position = 0
            await self._move_servo()

    async def async_set_cover_position(self, position):
        """Set the position of the servo drive from 0 to 10."""
        self._target_position = max(0, min(10, position))  # Limit the value between 0 and 10
        await self._move_servo()

    async def _move_servo(self):
        """Move the servo to the target position using time delays."""
        if self._target_position == self._position:
            return  # Already in the target position, no need to move

        self._is_moving = True
        movement_time = abs(self._target_position - self._position) * self._max_time_to_move / 10  # Calculate movement time

        if self._target_position > self._position:
            # Move towards opening
            await self._relay_on()
        else:
            # Move towards closing
            await self._relay_off()

        # Wait for the movement to complete
        await asyncio.sleep(movement_time)

        # After movement, check the final position
        self._position = self._target_position
        self._is_moving = False

        # Turn off relay once movement is completed
        await self._relay_off() if self._position == 0 else self._relay_on()

    async def async_reset_position(self):
        """Reset the servo drive position in case of desynchronization."""
        # In case of desynchronization, manually set the correct position
        self._position = self._target_position
        self._is_moving = False
        await self._relay_off()  # Stop the relay if it was on

    async def async_setup_services(hass: HomeAssistant):
        """Set up the services for the servo servo drive."""
        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            "open_servo_drive",
            {},
            "async_open",
        )

        platform.async_register_entity_service(
            "close_servo_drive",
            {},
            "async_close",
        )

        platform.async_register_entity_service(
            "set_servo_drive_position",
            {
                "position": int,
            },
            "async_set_cover_position",
        )
