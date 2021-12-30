from gpiozero import Button


class InputPin:
    def __init__(self, pin, pull_up, bounce_time, pin_factory, on_on, on_off):
        if pull_up is None:
            active_state = True
            self._invert_value = False
        elif pull_up is True:
            active_state = None
            self._invert_value = True
        elif pull_up is False:
            active_state = None
            self._invert_value = False

        self._button = Button(
            pin=pin,
            pull_up=pull_up,
            active_state=active_state,
            bounce_time=bounce_time,
            pin_factory=pin_factory,
        )

        self._button.when_pressed = on_off if self._invert_value else on_on
        self._button.when_released = on_on if self._invert_value else on_off

    def close(self):
        self._button.when_pressed = None
        self._button.when_released = None
        self._button.close()

    @property
    def value(self):
        if self._invert_value:
            return 1 if self._button.value == 0 else 0
        return self._button.value
