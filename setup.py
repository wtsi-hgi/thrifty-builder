from setuptools import setup, find_packages


try:
    from pypandoc import convert
    def read_markdown(file: str) -> str:
        return convert(file, "rst")
except ImportError:
    def read_markdown(file: str) -> str:
        return open(file, "r").read()

setup(
    name="thriftybuilder",
    version="0.0.1",
    packages=find_packages(exclude=["tests"]),
    install_requires=open("requirements.txt", "r").readlines(),
    url="https://github.com/wtsi-hgi/thrifty-builder",
    license="MIT",
    description="",
    long_description=read_markdown("README.md"),
    zip_safe=True
)
