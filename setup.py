from setuptools import setup, find_packages

setup(
        name='tasksync',
        version='1.0.1',
        description='Syncs task repositories.',

        author='Richard Burnison',
        author_email='richard@burnison.ca',
        url='http://www.burnison.ca/',

        packages=find_packages(),

        include_package_data=True,
        zip_safe=False,

        install_requires=[
            'google-api-python-client>=1.6.5',
            'httplib2>=0.10.3',
            'taskw==1.2.0',
            'oauth2client==4.1.3',
        ],

        tests_require=[
            'mockito<=0.6.0',
        ],

        entry_points={
            'console_scripts':['tasksync = tasksync.main:main']
        }
)
