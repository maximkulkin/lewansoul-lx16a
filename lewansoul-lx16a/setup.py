from setuptools import setup

setup(
    name='lewansoul_lx16a',
    version='0.1',
    description='Driver to control LewanSoul LX-16A servos',
    author='Maxim Kulkin',
    author_email='maxim.kulkin@gmail.com',
    url='https://github.com/maximkulkin/lewansoul-lx16a',
    py_modules=['lewansoul_lx16a'],
    license='MIT',
    requires=['pyserial'],
)
