import versioneer
from setuptools import (setup, find_packages)

with open('requirements.txt', 'rt') as f:
    requirements = f.read().splitlines()


setup(
    name='lightpath',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='BSD',
    author='SLAC National Accelerator Laboratory',
    packages=find_packages(),
    include_package_data=True,
    scripts=['bin/lightpath']
)
