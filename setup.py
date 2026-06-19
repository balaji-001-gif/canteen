from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from canteen_management import __version__ as version

setup(
    name="canteen_management",
    version=version,
    description="Canteen Management System with integrated POS Billing for ERPNext v15+",
    author="Your Company",
    author_email="admin@yourcompany.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
