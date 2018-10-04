__all__ = [
    'ServoController',
    'TimeoutError',
]


from serial.serialutil import Timeout
from functools import partial
from itertools import chain
import threading
import logging


CMD_SERVO_MOVE = 3
CMD_ACTION_GROUP_RUN = 6
CMD_ACTION_STOP = 7
CMD_ACTION_SPEED = 11
CMD_GET_BATTERY_VOLTAGE = 15
CMD_MULT_SERVO_UNLOAD = 20
CMD_MULT_SERVO_POS_READ = 21


def lower_byte(value):
    return int(value) % 256


def higher_byte(value):
    return int(value / 256) % 256


def word(low, high):
    return int(low) + int(high)*256


def hex_data(data):
    return '[%s]' % ', '.join(['0x%02x' % x for x in data])


def clamp(range_min, range_max, value):
    return min(range_max, max(range_min, value))


class TimeoutError(RuntimeError):
    pass


LOGGER = logging.getLogger('lewansoul.servos.lx16a')


class ServoController(object):
    def __init__(self, serial, timeout=1):
        self._serial = serial
        self._timeout = timeout
        self._lock = threading.RLock()
        self._responses = []

    def _command(self, command, *params):
        length = 2 + len(params)
        with self._lock:
            data = self._serial.read_all()
            if data:
                LOGGER.debug('Got this while preparing to send: %s', hex_data(data))

            LOGGER.debug('Sending servo control packet: %s', hex_data([
                0x55, 0x55, length, command, *params
            ]))
            self._serial.write(bytearray([
                0x55, 0x55, length, command, *params
            ]))

    def _wait_for_response(self, command, timeout=None):
        timeout = Timeout(timeout or self._timeout)

        def read(size=1):
            self._serial.timeout = timeout.time_left()
            data = self._serial.read(size)
            if len(data) != size:
                raise TimeoutError()
            return data

        while True:
            data = []
            data += read(1)
            if data[-1] != 0x55:
                LOGGER.error(
                    'Got unexpected octet while waiting for response header: %02x',
                    data[-1]
                )
                continue
            data += read(1)
            if data[-1] != 0x55:
                LOGGER.error(
                    'Got unexpected octet while waiting for response header: %02x',
                    data[-1]
                )
                continue
            data += read(2)
            length = data[2]
            cmd = data[3]

            data += read(length-2) if length > 2 else []
            params = data[4:]

            LOGGER.debug('Got command %s response: %s', cmd, hex_data(data))
            self._responses.append([cmd] + params)

            return params

    def _query(self, command, *params, timeout=None):
        with self._lock:
            self._command(command, *params)
            return self._wait_for_response(command, timeout=timeout)

    def move(self, positions, time=0):
        """Command multiple servos to move to given positions in given time.

        Args:
            positoins - dict mapping servo IDs to corresponding positions
            time - int number of milliseconds for move
        """
        time = clamp(0, 30000, time)

        self._command(
            CMD_SERVO_MOVE, len(positions),
            lower_byte(time), higher_byte(time),
            *chain(*[
                (servo_id, lower_byte(pos), higher_byte(pos))
                for servo_id, position in positions.items()
                for pos in [clamp(0, 10000, position)]
            ])
        )

    def get_positions(self, servo_ids):
        """Reads positions of servos with given IDs and returns a map
        from servo ID to corresponding position.

        Args:
            servo_ids - list of servo IDs (ints)

        Returns:
            dict mapping servo ID to corresponding position
        """
        response = self._query(CMD_MULT_SERVO_POS_READ, len(servo_ids), *servo_ids)
        return {
            response[1 + 3*i]: word(response[2 + 3*i], response[3 + 3*i])
            for i in range(response[0])
        }

    def unload(self, servo_ids):
        """Switches off motors of servos with given IDs.

        Args:
            servo_ids - list of servo IDs (ints)
        """
        self._command(CMD_MULT_SERVO_UNLOAD, len(servo_ids), *servo_ids)

    def get_battery_voltage(self):
        """Returns servo controller power supply voltage level in millivolts."""
        response = self._query(CMD_GET_BATTERY_VOLTAGE)
        return word(response[0], response[1])
