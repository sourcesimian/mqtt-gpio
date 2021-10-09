from setuptools import setup

setup(
    name="mqtt-gpio",
    version="0.0.0",
    description="MQTT to GPIO pin connector service",
    author="Source Simian",
    url="https://github.com/sourcesimian/mqtt-gpio",
    license="MIT",
    packages=['mqtt_gpio'],
    install_requires=open('python3-requirements.txt').readlines(),
    entry_points={
        "console_scripts": [
            "mqtt-gpio=mqtt_gpio.main:cli",
        ]
    },
)
