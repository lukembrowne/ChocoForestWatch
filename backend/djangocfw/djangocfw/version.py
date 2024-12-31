# Format: (major, minor, patch, release_stage)
# Release stages: 'alpha', 'beta', 'rc', 'final'
VERSION = (0, 1, 1, 'beta')

def get_version():
    version = '%s.%s.%s' % (VERSION[0], VERSION[1], VERSION[2])
    if VERSION[3] != 'final':
        version = f'{version}-{VERSION[3]}'
    return version

__version__ = get_version() 