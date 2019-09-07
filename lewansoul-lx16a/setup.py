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
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=['pyserial'],
)
