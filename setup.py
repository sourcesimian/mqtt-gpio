from setuptools import setup

setup(
    name="mqtt-gpio",
    version=open('version', 'rt', encoding="utf8").read().strip(),
    description="GPIO pin to MQTT bridge service",
    author="Source Simian",
    url="https://github.com/sourcesimian/mqtt-gpio",
    license="MIT",
    packages=['mqtt_gpio'],
    install_requires=open('python3-requirements.txt', encoding="utf8").readlines(),
    entry_points={
        "console_scripts": [
            "mqtt-gpio=mqtt_gpio.main:cli",
        ]
    },
)
