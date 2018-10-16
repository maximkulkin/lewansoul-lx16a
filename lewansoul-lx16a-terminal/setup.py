from setuptools import setup
import os
import os.path
import fnmatch

def find_files(directory, pattern, recursive=True):
    files = []
    for dirpath, dirnames, filenames in os.walk(directory, topdown=True):
        if not recursive:
            while dirnames:
                del dirnames[0]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if fnmatch.fnmatch(filepath, pattern):
                files.append(filepath)

    return files


setup(
    name='lewansoul_lx16a_terminal',
    version='0.1',
    description='GUI to configure and control LewanSoul LX-16A servos',
    author='Maxim Kulkin',
    author_email='maxim.kulkin@gmail.com',
    url='https://github.com/maximkulkin/lewansoul-lx16a',
    py_modules=['lewansoul_lx16a_terminal'],
    scripts=['scripts/lewansoul_lx16a_terminal'],
    data_files=[
        ('resources', find_files('resources', '*.ui')),
    ],
    include_package_data=True,
    license='MIT',
    install_requires=['lewansoul_lx16a', 'pyserial', 'PyQt5'],
)
