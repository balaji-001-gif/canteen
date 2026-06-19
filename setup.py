import re
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

with open("canteen_management/__init__.py") as f:
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
    if not match:
        raise RuntimeError("Unable to find version string in canteen_management/__init__.py")
    version = match.group(1)

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
