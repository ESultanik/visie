from setuptools import setup, find_packages

setup(
    name='visie',
    description='Visie is a simple initialism enumerator. It helps you name things.',
    url='https://github.com/ESultanik/visie',
    author='Evan Sultanik',
    version='0.1.1',
    packages=find_packages(),
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
