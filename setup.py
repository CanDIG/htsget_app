from setuptools import setup, find_packages

requirements = [
        'Connexion==1.4.2',
        'Flask==1.0.3',
        'minio==4.0.17',
        'ga4gh-dos-schemas==0.4.2',
        'pysam==0.15.2'
]

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
    install_requires=requirements,
    include_package_data=True,
    keywords='htsget_app',
    name='htsget_app',
    packages=find_packages(include=['htsget_server']),
    url="https://github.com/CanDIG/htsget_app",
    version='0.1.0'
)