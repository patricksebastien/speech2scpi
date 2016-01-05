Speech recognition and tts for your SCPI enabled oscilloscope
http://www.workinprogress.ca/software/speech2scpi

# Disclaimer
This software is just a proof of concept. Coded “sur un coin de table” in just a few hours.

# Installing
Works only on LINUX. Dependencies are:

- Python 2.7
- pip install zeroconf
- pip install requests
- pip install cython
- sudo apt-get install liblo-dev
- curl -O http://das.nasophon.de/download/pyliblo-0.10.0.tar.gz
&& tar xzpf pyliblo-0.10.0.tar.gz
&& ./setup.py build
&& sudo ./setup.py install
- sudo pip install pyvona

# Using

- If you want TTS, you need to create an account for <a href="https://www.ivona.com/ap/signin">ivona</a> && insert the keys in speech2scpi.py -> v = pyvona.create_voice(‘Access Key’, ‘Secret Key’)
- Connect your SCPI enabled oscilloscope in the HUB
- python speech2scpi.py
- Speak (ie: channel 2 on)
