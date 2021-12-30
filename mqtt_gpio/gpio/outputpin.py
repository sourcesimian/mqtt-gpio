from gpiozero import LED


class OutputPin:
    def __init__(self, pin, pull_up, initial_value, pin_factory):
        if pull_up is None:
            active_high = True
            self._invert_value = False
        elif pull_up is True:
            active_high = True
            self._invert_value = False
        elif pull_up is False:
            active_high = False
            self._invert_value = True

        if initial_value is not None and active_high is False:
            initial_value = not initial_value

        self._led = LED(
            pin=pin,
            active_high=active_high,
            initial_value=initial_value,
            pin_factory=pin_factory,
        )

    @property
    def value(self):
        if self._invert_value is True:
            return 1 if self._led.value == 0 else 0
        return self._led.value

    @value.setter
    def value(self, value):
        if self._invert_value:
            self._led.value = 1 if value == 0 else 0
        else:
            self._led.value = value

    def close(self):
        self._led.close()
