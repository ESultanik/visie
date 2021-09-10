import os
from setuptools import setup, find_packages

SETUP_DIR = os.path.dirname(os.path.realpath(__file__))
README_PATH = os.path.join(SETUP_DIR, "README.md")

with open(README_PATH, "r") as readme:
    README = readme.read()

setup(
    name='visie',
    description='Visie is a simple initialism enumerator. It helps you name things.',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://github.com/ESultanik/visie',
    author='Evan Sultanik',
    version='0.1.1',
    packages=find_packages(exclude=["test"]),
    python_requires='>=3.6',
    install_requires=[],
    extras_require={
        "dev": ["flake8", "pytest", "twine", "mypy>=0.812"]
    },
    entry_points={
        'console_scripts': [
            'visie = visie.__main__:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Topic :: Text Processing :: General',
        'Topic :: Utilities'
    ]
)
