from setuptools import setup

setup(
    name='lewansoul_lx16a_terminal',
    version='0.1',
    description='GUI to configure and control LewanSoul LX-16A servos',
    author='Maxim Kulkin',
    author_email='maxim.kulkin@gmail.com',
    url='https://github.com/maximkulkin/lewansoul-lx16a',
    py_modules=['lewansoul_lx16a_terminal'],
    scripts=['scripts/lewansoul_lx16a_terminal'],
    include_package_data=True,
    license='MIT',
    requires=['lewansoul_lx16a', 'pyserial', 'PyQt5'],
)
