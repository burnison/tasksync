from setuptools import setup, find_packages

setup(
        name='tasksync',
        version='1.0.0',
        description='Syncs task repositories.',

        author='Richard Burnison',
        author_email='richard@burnison.ca',
        url='http://www.burnison.ca/',

        packages=['tasksync'],
        test_suite='nose.collector',

        install_requires=[
            'google-api-python-client>=1.0',
            'httplib2>=0.7',
            'twiggy',
            'taskw>=0.4.5'],
        tests_require=[
            'nose>=1.0',
            'mockito>=0.5'],
)
