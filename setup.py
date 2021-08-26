from setuptools import setup, find_packages

test_requirements = []
with open("requirements_dev.txt") as dev_requirements:
    for line in dev_requirements:
        line = line.strip()
        if len(line) == 0:
            continue
        if line[0] == '#':
            continue

        version_pin = line.split()[0]
        test_requirements.append(version_pin)

setup(
    author="Jackson Zheng",
    author_email="j75zheng@edu.uwaterloo.ca",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="CanDIG htsget API that follows the htsget standard",
    include_package_data=True,
    keywords='htsget_app',
    name='htsget_app',
    packages=find_packages(include=['htsget_server']),
    tests_require=test_requirements,
    url="https://github.com/CanDIG/htsget_app",
    version='0.1.3'
)
