from setuptools import setup, find_packages

# Read the contents of your README file
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read the contents of your requirements file
with open('all_requirements.txt', 'r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

setup(
    name='blockhouse-ml',  # Replace with your package name
    version='0.1.0',  # Start with a version like 0.1.0
    author='blockhouse-team',
    description='For developing and deploying machine learning models for blockhouse',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=requirements,
    python_requires='>=3.7',
    extras_require={
        'train': ['matplotlib', 'jupyter', 'jupyterlab', 'ray[tune]', 'wandb'],
    }
)