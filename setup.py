import versioneer
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="lightpath",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD",
    author="SLAC National Accelerator Laboratory",
    packages=find_packages(),
    package_data={
        "lightpath": ["ui/*.ui"],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'lightpath = lightpath.__main__:entrypoint',
        ]
    },
)
