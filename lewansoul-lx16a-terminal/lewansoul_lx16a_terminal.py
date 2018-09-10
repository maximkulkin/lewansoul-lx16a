#!/usr/bin/env python3
"""
Terminal GUI for LewanSoul LX-16A servos

Author: Maxim Kulkin
Website: https://github.com/maximkulkin/lewansoul-lx16a
"""

import sys

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QApplication, QDialog, QMessageBox, QListWidgetItem)
from PyQt5.uic import loadUi as _loadUi

from collections import namedtuple
import pkg_resources
import logging
import serial
from serial.tools.list_ports import comports
import lewansoul_lx16a


def loadUi(path, widget):
    real_path = pkg_resources.resource_filename('lewansoul_lx16a_terminal', path)
    _loadUi(real_path, widget)


ServoConfiguration = namedtuple('ServoConfiguration', [
    'servo_id', 'position_limits', 'voltage_limits', 'max_temperature', 'position_offset',
])

ServoState = namedtuple('ServoState', [
    'servo_id', 'voltage', 'temperature',
    'mode', 'position', 'speed', 'motor_on', 'led_on', 'led_errors',
])


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


class ConfigurePositionOffsetDialog(QDialog):
    def __init__(self, servo):
        super(ConfigurePositionOffsetDialog, self).__init__()
        self._servo = servo

        loadUi('resources/ConfigurePositionOffset.ui', self)

        self.positionOffsetSlider.valueChanged.connect(self._on_slider_change)
        self.positionOffsetEdit.valueChanged.connect(self._on_edit_change)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    def _update_servo(self, deviation):
        self._servo.set_position_offset(deviation)

    def _on_slider_change(self, position):
        self.positionOffsetEdit.setValue(position)
        self._update_servo(position)

    def _on_edit_change(self, position):
        self.positionOffsetSlider.setValue(position)
        self._update_servo(position)

    @property
    def positionOffset(self):
        return self.positionOffsetEdit.value()

    @positionOffset.setter
    def positionOffset(self, value):
        self.positionOffsetEdit.setValue(value)


class ServoScanThread(QThread):
    servoFound = pyqtSignal(int)

    def __init__(self, controller):
        super(ServoScanThread, self).__init__()
        self._controller = controller

    def _servo_exists(self, id):
        try:
            servo_id = self._controller.get_servo_id(id, timeout=0.2)
            return (servo_id == id)
        except TimeoutError:
            return False

    def run(self):
        for servoId in range(1, 10):
            if self.isInterruptionRequested():
                break

            try:
                if self._servo_exists(servoId):
                    self.servoFound.emit(servoId)
            except lewansoul_lx16a.TimeoutError:
                pass

            self.yieldCurrentThread()


class GetServoConfigurationThread(QThread):
    servoConfigurationUpdated = pyqtSignal(ServoConfiguration)
    servoConfigurationTimeout = pyqtSignal()

    MAX_RETRIES = 5

    def __init__(self, servo):
        super(GetServoConfigurationThread, self).__init__()
        self._servo = servo

    @property
    def servo_id(self):
        return self._servo.servo_id

    def run(self):
        try:
            retries = 0
            while True:
                if self.isInterruptionRequested():
                    return

                try:
                    position_limits = self._servo.get_position_limits()
                    break
                except lewansoul_lx16a.TimeoutError:
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        raise
                    self.sleep(1)

            while True:
                if self.isInterruptionRequested():
                    return

                try:
                    voltage_limits = self._servo.get_voltage_limits()
                    break
                except lewansoul_lx16a.TimeoutError:
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        raise
                    self.sleep(1)

            while True:
                if self.isInterruptionRequested():
                    return

                try:
                    max_temperature = self._servo.get_max_temperature_limit()
                    break
                except lewansoul_lx16a.TimeoutError:
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        raise
                    self.sleep(1)

            while True:
                if self.isInterruptionRequested():
                    return

                try:
                    position_offset = self._servo.get_position_offset()
                    break
                except lewansoul_lx16a.TimeoutError:
                    retries += 1
                    if retries >= self.MAX_RETRIES:
                        raise
                    self.sleep(1)

            self.servoConfigurationUpdated.emit(ServoConfiguration(
                servo_id=self.servo_id,
                position_limits=position_limits,
                voltage_limits=voltage_limits,
                max_temperature=max_temperature,
                position_offset=position_offset,
            ))
        except lewansoul_lx16a.TimeoutError:
            self.servoConfigurationTimeout.emit()


class ServoMonitorThread(QThread):
    servoStateUpdated = pyqtSignal(ServoState)

    def __init__(self, servo):
        super(ServoMonitorThread, self).__init__()
        self._servo = servo

    def run(self):
        while not self.isInterruptionRequested():
            try:
                voltage = self._servo.get_voltage()
                temperature = self._servo.get_temperature()

                mode = self._servo.get_mode()
                if mode == 0:
                    position, speed = self._servo.get_position(), 0
                else:
                    position, speed = 0, self._servo.get_motor_speed()

                motor_on = self._servo.is_motor_on()
                led_on = self._servo.is_led_on()
                led_errors = self._servo.get_led_errors()

                self.servoStateUpdated.emit(ServoState(
                    servo_id=self._servo.servo_id,
                    voltage=voltage,
                    temperature=temperature,
                    mode=mode,
                    position=position,
                    speed=speed,
                    motor_on=motor_on,
                    led_on=led_on,
                    led_errors=led_errors,
                ))
            except lewansoul_lx16a.TimeoutError:
                pass

            self.sleep(1)


class Terminal(QWidget):
    logger = logging.getLogger('lewansoul.terminal')

    def __init__(self):
        super(Terminal, self).__init__()

        self.connection = False
        self.selected_servo_id = False
        self.servo = None

        self._available_ports = []

        loadUi('resources/ServoTerminal.ui', self)

        self.configureIdButton.clicked.connect(self._configure_servo_id)
        self.configurePositionLimitsButton.clicked.connect(self._configure_position_limits)
        self.configureVoltageLimitsButton.clicked.connect(self._configure_voltage_limits)
        self.configureMaxTemperatureButton.clicked.connect(self._configure_max_temperature)
        self.configurePositionOffsetButton.clicked.connect(self._configure_position_offset)

        self.portCombo.currentTextChanged.connect(self._on_port_change)
        self.refreshPortsButton.clicked.connect(self._refresh_ports)
        self.servoList.currentItemChanged.connect(lambda curItem, prevItem: self._on_servo_selected(curItem))
        self.scanServosButton.clicked.connect(self._scan_servos)

        self.servoOrMotorSwitch.valueChanged.connect(self._on_servo_motor_switch)
        self.speedSlider.valueChanged.connect(self._on_speed_slider_change)
        self.speedEdit.valueChanged.connect(self._on_speed_edit_change)

        self.positionSlider.valueChanged.connect(self._on_position_slider_change)
        self.positionEdit.valueChanged.connect(self._on_position_edit_change)

        self.motorOnButton.clicked.connect(self._on_motor_on_button)
        self.ledOnButton.clicked.connect(self._on_led_on_button)
        self.clearLedErrorsButton.clicked.connect(self._on_clear_led_errors_button)

        self._servoScanThread = None
        self._servoReadConfigurationThread = None
        self._servoStateMonitorThread = None

        self.connectionGroup.setEnabled(False)

        self._refresh_ports()
        self._on_servo_selected(None)

        self.show()

    def _refresh_ports(self):
        old_text = self.portCombo.currentText()

        self._available_ports = sorted(comports())

        self.portCombo.blockSignals(True)
        self.portCombo.clear()
        self.portCombo.addItem('')
        self.portCombo.addItems([port.device for port in self._available_ports])
        self.portCombo.setCurrentText(old_text)
        self.portCombo.blockSignals(False)

        if self.portCombo.currentText() != old_text:
            self._on_port_change(self.portCombo.currentIndex())

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
                QMessageBox.critical(self, "Connection error", "Failed to connect to device")

    def _scan_servos(self):
        if not self.controller:
            return

        def scanStarted():
            self.servoList.clear()
            self.scanServosButton.setText('Stop Scan')
            self.scanServosButton.setEnabled(True)

        def scanFinished():
            self.scanServosButton.setText('Scan Servos')
            self.scanServosButton.setEnabled(True)
            self._servoScanThread = None

        def servoFound(servoId):
            item = QListWidgetItem('Servo ID=%s' % servoId)
            item.setData(Qt.UserRole, servoId)
            self.servoList.addItem(item)

        if not self._servoScanThread:
            self._servoScanThread = ServoScanThread(self.controller)
            self._servoScanThread.servoFound.connect(servoFound)
            self._servoScanThread.started.connect(scanStarted)
            self._servoScanThread.finished.connect(scanFinished)

        self.scanServosButton.setEnabled(False)
        if self._servoScanThread.isRunning():
            self._servoScanThread.requestInterruption()
        else:
            self._servoScanThread.start()

    def _on_servo_selected(self, item):
        servo_id = None
        if item is not None:
            servo_id = item.data(Qt.UserRole)

        if servo_id:
            self.servo = self.controller.servo(servo_id)
            self.servoGroup.setEnabled(True)

            def servo_configuration_updated(details):
                self.servoIdLabel.setText(str(details.servo_id))
                self.positionLimits.setText('%d .. %d' % details.position_limits)
                self.voltageLimits.setText('%d .. %d' % details.voltage_limits)
                self.maxTemperature.setText(str(details.max_temperature))
                self.positionOffset.setText(str(details.position_offset))

                if self._servoStateMonitorThread:
                    self._servoStateMonitorThread.requestInterruption()

                self._servoStateMonitorThread = ServoMonitorThread(self.servo)
                self._servoStateMonitorThread.servoStateUpdated.connect(self._update_servo_state)
                self._servoStateMonitorThread.start()

            def servo_configuration_timeout():
                self._on_servo_selected(None)
                QMessageBox.warning(self, "Timeout", "Timeout reading servo data")

            if self._servoReadConfigurationThread and self._servoReadConfigurationThread.servo_id != servo_id:
                self._servoReadConfigurationThread.requestInterruption()
                self._servoReadConfigurationThread.wait()
                self._servoReadConfigurationThread = None

            if self._servoReadConfigurationThread is None:
                self._servoReadConfigurationThread = GetServoConfigurationThread(self.servo)
                self._servoReadConfigurationThread.servoConfigurationUpdated.connect(servo_configuration_updated)
                self._servoReadConfigurationThread.servoConfigurationTimeout.connect(servo_configuration_timeout)
                self._servoReadConfigurationThread.start()
        else:
            if self._servoStateMonitorThread:
                self._servoStateMonitorThread.requestInterruption()
                self._servoStateMonitorThread.wait()
                self._servoStateMonitorThread = None

            if self._servoReadConfigurationThread:
                self._servoReadConfigurationThread.requestInterruption()
                self._servoReadConfigurationThread.wait()
                self._servoReadConfigurationThread = None

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
        dialog.minVoltage, dialog.maxVoltage = self.servo.get_voltage_limits()
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

    def _configure_position_offset(self):
        if not self.servo:
            return

        dialog = ConfigurePositionOffsetDialog(self.servo)
        old_position_offset = self.servo.get_position_offset()
        dialog.positionOffset = old_position_offset
        if dialog.exec_():
            self.logger.info('Setting position offset limit to %d' % (dialog.positionOffset))
            self.servo.set_position_offset(dialog.positionOffset)
            self.servo.save_position_offset()
            self.positionOffset.setText(str(dialog.positionOffset))
        else:
            self.servo.set_position_offset(old_position_offset)

    def _on_servo_motor_switch(self, value):
        try:
            if value == 0:
                self.servoOrMotorModeUi.setCurrentIndex(0)
                self.servo.set_servo_mode()
            else:
                self.servoOrMotorModeUi.setCurrentIndex(1)
                self.servo.set_motor_mode()
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout changing motor mode")

    def _on_speed_slider_change(self, speed):
        try:
            self.speedEdit.setValue(speed)
            self.logger.info('Setting motor speed to %d' % speed)
            self.servo.set_motor_mode(speed)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout updating motor speed")

    def _on_speed_edit_change(self, speed):
        try:
            self.speedSlider.setValue(speed)
            self.logger.info('Setting motor speed to %d' % speed)
            self.servo.set_motor_mode(speed)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout updating motor speed")

    def _on_position_slider_change(self, position):
        try:
            self.positionEdit.setValue(position)
            self.logger.info('Setting servo position to %d' % position)
            self.servo.move(position)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout setting servo position")

    def _on_position_edit_change(self, position):
        try:
            self.positionSlider.setValue(position)
            self.logger.info('Setting servo position to %d' % position)
            self.servo.move(position)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout setting servo position")

    def _on_motor_on_button(self):
        if not self.servo:
            return

        try:
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
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout updating motor state")

    def _on_led_on_button(self):
        if not self.servo:
            return

        try:
            if self.servo.is_led_on():
                self.servo.led_off()
                self.ledOnButton.setChecked(False)
            else:
                self.servo.led_on()
                self.ledOnButton.setChecked(True)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout updating LED state")

    def _on_clear_led_errors_button(self):
        if not self.servo:
            return

        try:
            self.servo.set_led_errors(0)
        except lewansoul_lx16a.TimeoutError:
            QMessageBox.critical(self, "Timeout", "Timeout resetting LED errors")

    def _update_servo_state(self, servo_state):
        self.currentVoltage.setText('Voltage: %d' % servo_state.voltage)
        self.currentTemperature.setText('Temperature: %d' % servo_state.temperature)
        self.motorOnButton.setChecked(servo_state.motor_on)
        self.ledOnButton.setChecked(servo_state.led_on)
        if servo_state.led_errors:
            messages = []
            if lewansoul_lx16a.SERVO_ERROR_OVER_TEMPERATURE | servo_state.led_errors:
                messages.append('Overheating')
            if lewansoul_lx16a.SERVO_ERROR_OVER_VOLTAGE | servo_state.led_errors:
                messages.append('Voltage is out of limits')
            if lewansoul_lx16a.SERVO_ERROR_LOCKED_ROTOR | servo_state.led_errors:
                messages.append('Locked rotor')
            self.ledErrors.setText('\n'.join(messages))
            self.clearLedErrorsButton.setEnabled(True)
        else:
            self.ledErrors.setText('')
            self.clearLedErrorsButton.setEnabled(False)

        if self.servoOrMotorModeUi.currentIndex() == 0:
            self.currentPosition.setText(str(servo_state.position))
        else:
            self.currentSpeed.setText(str(servo_state.speed))

    def closeEvent(self, event):
        if self._servoScanThread:
            self._servoScanThread.requestInterruption()
            self._servoScanThread.wait()
            self._servoScanThread = None

        if self._servoReadConfigurationThread:
            self._servoReadConfigurationThread.requestInterruption()
            self._servoReadConfigurationThread.wait()
            self._servoReadConfigurationThread = None

        if self._servoStateMonitorThread:
            self._servoStateMonitorThread.requestInterruption()
            self._servoStateMonitorThread.wait()
            self._servoStateMonitorThread = None

        if self.connection:
            self.connection.close()

        event.accept()


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    terminal = Terminal()
    sys.exit(app.exec_())
