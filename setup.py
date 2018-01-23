from setuptools import setup, find_packages

from thriftybuilder.meta import VERSION, DESCRIPTION, PACKAGE_NAME, EXECUTABLE_NAME

try:
    from pypandoc import convert
    def read_markdown(file: str) -> str:
        return convert(file, "rst")
except ImportError:
    def read_markdown(file: str) -> str:
        return open(file, "r").read()

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    packages=find_packages(exclude=["tests"]),
    install_requires=open("requirements.txt", "r").readlines(),
    url="https://github.com/wtsi-hgi/thrifty-builder",
    license="MIT",
    description=DESCRIPTION,
    long_description=read_markdown("README.md"),
        entry_points={
        "console_scripts": [
            f"{EXECUTABLE_NAME}={PACKAGE_NAME}.cli:entrypoint"
        ]
    },
    zip_safe=True
)
