from setuptools import setup

setup(
    name='behave_parallel_runner',
    version='1.0.0',
    packages=['parallel_runner'],
    entry_points={
        'console_scripts': [
            'behave_parallel_runner = parallel_runner.__main__:main'
        ]
    },
    install_requires=[
        'pytz == 2016.10',
    ],
)
