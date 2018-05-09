import versioneer
from setuptools import (setup, find_packages)

with open('requirements.txt') as f:
        requirements = f.read().split()

# Temporary hack until filestore is on PyPI, needed because
# `pip install -r requirements.txt` works with git URLs, but `install_requires`
# does not.
requirements = [r for r in requirements if not r.startswith('git+')]

setup(name     = 'lightpath',
      version  = versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      license  = 'BSD',
      author   = 'SLAC National Accelerator Laboratory',

      packages    = find_packages(),
      include_package_data=True,
      scripts=['bin/lightpath']
    )
