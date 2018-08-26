#!/usr/bin/env python3
"""
Terminal GUI for LewanSoul LX-16A servos

Author: Maxim Kulkin
Website: https://github.com/maximkulkin/lewansoul-lx16a
"""

import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QApplication, QDialog, QListWidgetItem)
from PyQt5.uic import loadUi as _loadUi

import pkg_resources
import logging
import serial
from serial.tools.list_ports import comports
import lewansoul_lx16a


def loadUi(path, widget):
    real_path = pkg_resources.resource_filename('lewansoul_lx16a_terminal', path)
    _loadUi(real_path, widget)


class ConfigureIdDialog(QDialog):
    def __init__(self):
        super(ConfigureIdDialog, self).__init__()

        loadUi('resources/ConfigureId.ui', self)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    @property
    def servoId(self):
        return self.servoIdEdit.value()

    @servoId.setter
    def servoId(self, value):
        self.servoIdEdit.setValue(value)


class ConfigurePositionLimitsDialog(QDialog):
    def __init__(self):
        super(ConfigurePositionLimitsDialog, self).__init__()

        loadUi('resources/ConfigurePositionLimits.ui', self)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    @property
    def minPosition(self):
        return self.rangeMin.value()

    @minPosition.setter
    def minPosition(self, value):
        self.rangeMin.setValue(value)

    @property
    def maxPosition(self):
        return self.rangeMax.value()

    @maxPosition.setter
    def maxPosition(self, value):
        self.rangeMax.setValue(value)


class ConfigureVoltageLimitsDialog(QDialog):
    def __init__(self):
        super(ConfigureVoltageLimitsDialog, self).__init__()

        loadUi('resources/ConfigureVoltageLimits.ui', self)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    @property
    def minVoltage(self):
        return self.rangeMin.value()

    @minVoltage.setter
    def minVoltage(self, value):
        self.rangeMin.setValue(value)

    @property
    def maxVoltage(self):
        return self.rangeMax.value()

    @maxVoltage.setter
    def maxVoltage(self, value):
        self.rangeMax.setValue(value)


class ConfigureMaxTemperatureDialog(QDialog):
    def __init__(self):
        super(ConfigureMaxTemperatureDialog, self).__init__()

        loadUi('resources/ConfigureMaxTemperature.ui', self)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    @property
    def maxTemperature(self):
        return self.maxTemperatureEdit.value()

    @maxTemperature.setter
    def maxTemperature(self, value):
        self.maxTemperatureEdit.setValue(value)


class Terminal(QWidget):
    logger = logging.getLogger('lewansoul.terminal')

    def __init__(self):
        super(Terminal, self).__init__()

        self.connection = False
        self.selected_servo_id = False
        self.servo = None

        self._available_ports = sorted(comports())

        loadUi('resources/ServoTerminal.ui', self)

        self.configureIdButton.clicked.connect(self._configure_servo_id)
        self.configurePositionLimitsButton.clicked.connect(self._configure_position_limits)
        self.configureVoltageLimitsButton.clicked.connect(self._configure_voltage_limits)
        self.configureMaxTemperatureButton.clicked.connect(self._configure_max_temperature)

        self.portCombo.currentTextChanged.connect(self._on_port_change)
        self.servoList.currentItemChanged.connect(lambda curItem, prevItem: self._on_servo_selected(curItem))
        self.scanServosButton.clicked.connect(self._scan_servos)

        self.servoOrMotorSwitch.valueChanged.connect(self._on_servo_motor_switch)
        self.speedSlider.valueChanged.connect(self._on_speed_slider_change)
        self.speedEdit.valueChanged.connect(self._on_speed_edit_change)

        self.positionSlider.valueChanged.connect(self._on_position_slider_change)
        self.positionEdit.valueChanged.connect(self._on_position_edit_change)

        self.portCombo.addItem('')
        self.portCombo.addItems([port.device for port in self._available_ports])

        self.motorOnButton.clicked.connect(self._on_motor_on_button)
        self.ledOnButton.clicked.connect(self._on_led_on_button)

        self.servoPollTimer = QTimer()
        self.servoPollTimer.setInterval(1000)
        self.servoPollTimer.timeout.connect(self._refresh_servo_data)

        self.connectionGroup.setEnabled(False)
        self._on_servo_selected(None)

        self.show()

    def _on_port_change(self, portIdx):
        self._connect_to_port(self.portCombo.currentText())

    def _connect_to_port(self, device):
        if self.connection:
            self.connection.close()
            self.logger.info('Disconnected')
            self.connection = None
            self.controller = None
            self.connectionGroup.setEnabled(False)
            self.servoList.clear()
            self._on_servo_selected(None)

        if device:
            self.logger.info('Connecting to port %s' % device)
            try:
                self.connection = serial.Serial(device, 115200, timeout=1)
                self.controller = lewansoul_lx16a.ServoController(self.connection, timeout=1)
                self.connectionGroup.setEnabled(True)
                self.logger.info('Connected to {}'.format(device))
            except serial.serialutil.SerialException as e:
                self.logger.error('Failed to connect to port {}'.format(device))

    def _scan_servos(self):
        if not self.connection:
            return

        self.servoList.clear()

        for servoId in range(1, 40):
            try:
                if not self._servo_exists(servoId):
                    continue

                item = QListWidgetItem('Servo ID=%s' % servoId)
                item.setData(Qt.UserRole, servoId)
                self.servoList.addItem(item)
            except lewansoul_lx16a.TimeoutError:
                pass

    def _on_servo_selected(self, item):
        servo_id = None
        if item is not None:
            servo_id = item.data(Qt.UserRole)

        if servo_id:
            self.servo = self.controller.servo(servo_id)
            self.servoGroup.setEnabled(True)

            self.servoIdLabel.setText(str(servo_id))
            self.positionLimits.setText('%d .. %d' % self.servo.get_position_limits())
            self.voltageLimits.setText('%d .. %d' % self.servo.get_voltage_limits())
            self.maxTemperature.setText(str(self.servo.get_max_temperature_limit()))

            self._refresh_servo_data()
            self.servoPollTimer.start()
        else:
            self.servoPollTimer.stop()
            self.servo = None

            self.servoIdLabel.setText('')
            self.positionLimits.setText('')
            self.voltageLimits.setText('')
            self.maxTemperature.setText('')

            self.currentVoltage.setText('Voltage:')
            self.currentTemperature.setText('Temperature:')
            self.currentPosition.setText('')

            self.servoGroup.setEnabled(False)

    def _configure_servo_id(self):
        if not self.servo:
            return

        dialog = ConfigureIdDialog()
        dialog.servoId = self.servo.get_servo_id()
        if dialog.exec_():
            self.logger.info('Setting servo ID to %d' % dialog.servoId)
            self.servo.set_servo_id(dialog.servoId)
            self.servo = self.controller.servo(dialog.servoId)
            self.servoIdLabel.setText(str(dialog.servoId))

    def _configure_position_limits(self):
        if not self.servo:
            return

        dialog = ConfigurePositionLimitsDialog()
        dialog.minPosition, dialog.maxPosition = self.servo.get_position_limits()
        if dialog.exec_():
            self.logger.info('Setting position limits to %d..%d' % (dialog.minPosition, dialog.maxPosition))
            self.servo.set_position_limits(dialog.minPosition, dialog.maxPosition)
            self.positionLimits.setText('%d .. %d' % (dialog.minPosition, dialog.maxPosition))

    def _configure_voltage_limits(self):
        if not self.servo:
            return

        dialog = ConfigureVoltageLimitsDialog()
        dialog.minPosition, dialog.maxPosition = self.servo.get_voltage_limits()
        if dialog.exec_():
            self.logger.info('Setting voltage limits to %d..%d' % (dialog.minVoltage, dialog.maxVoltage))
            self.servo.set_voltage_limits(dialog.minVoltage, dialog.maxVoltage)
            self.voltageLimits.setText('%d .. %d' % (dialog.minVoltage, dialog.maxVoltage))

    def _configure_max_temperature(self):
        if not self.servo:
            return

        dialog = ConfigureMaxTemperatureDialog()
        dialog.maxTemperature = self.servo.get_max_temperature_limit()
        if dialog.exec_():
            self.logger.info('Setting max temperature limit to %d' % (dialog.maxTemperature))
            self.servo.set_max_temperature_limit(dialog.maxTemperature)
            self.maxTemperature.setText(str(dialog.maxTemperature))

    def _on_servo_motor_switch(self, value):
        if value == 0:
            self.servoOrMotorModeUi.setCurrentIndex(0)
            self.servo.set_servo_mode()
        else:
            self.servoOrMotorModeUi.setCurrentIndex(1)
            self.servo.set_motor_mode()

    def _on_speed_slider_change(self, speed):
        self.speedEdit.setValue(speed)
        self.logger.info('Setting motor speed to %d' % speed)
        self.servo.set_motor_mode(speed)

    def _on_speed_edit_change(self, speed):
        self.speedSlider.setValue(speed)
        self.logger.info('Setting motor speed to %d' % speed)
        self.servo.set_motor_mode(speed)

    def _on_position_slider_change(self, position):
        self.positionEdit.setValue(position)
        self.logger.info('Setting servo position to %d' % position)
        self.servo.move(position)

    def _on_position_edit_change(self, position):
        self.positionSlider.setValue(position)
        self.logger.info('Setting servo position to %d' % position)
        self.servo.move(position)

    def _on_motor_on_button(self):
        if not self.servo:
            return

        if self.servo.is_motor_on():
            if self.servo.get_mode() == 0:
                self.servo.motor_off()
            else:
                self.servo.set_motor_mode(0)
        else:
            if self.servo.get_mode() == 0:
                self.servo.motor_on()
            else:
                self.servo.set_motor_mode(self.speedSlider.value())

    def _on_led_on_button(self):
        if not self.servo:
            return

        if self.servo.is_led_on():
            self.servo.led_off()
            self.ledOnButton.setChecked(False)
        else:
            self.servo.led_on()
            self.ledOnButton.setChecked(True)

    def _refresh_servo_data(self):
        if not self.servo:
            return

        self.currentVoltage.setText('Voltage: %d' % self.servo.get_voltage())
        self.currentTemperature.setText('Temperature: %d' % self.servo.get_temperature())
        self.motorOnButton.setChecked(self.servo.is_motor_on())
        self.ledOnButton.setChecked(self.servo.is_led_on())

        if self.servoOrMotorModeUi.currentIndex() == 0:
            self.currentPosition.setText(str(self.servo.get_position()))
        else:
            self.currentSpeed.setText(str(self.servo.get_motor_speed()))

    def _servo_exists(self, id):
        try:
            servo_id = self.controller.get_servo_id(id, timeout=0.1)
            return (servo_id == id)
        except TimeoutError:
            return False

    def closeEvent(self, event):
        if self.connection:
            self.connection.close()

        event.accept()


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    terminal = Terminal()
    sys.exit(app.exec_())
