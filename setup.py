from setuptools import setup, find_packages

setup(
        name='tasksync',
        version='1.0.0',
        description='Syncs task repositories.',

        author='Richard Burnison',
        author_email='richard@burnison.ca',
        url='http://www.burnison.ca/',

        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,

        test_suite='nose.collector',

        install_requires=[
            'google-api-python-client>=1.0',
            'httplib2>=0.8',
            'twiggy',
            'taskw==0.5.1'],

        dependency_links = [
            'https://github.com/burnison/taskw/tarball/completed_task_inclusion#egg=taskw-0.5.1'],

        tests_require=[
            'nose>=1.0',
            'mockito>=0.5'],

        entry_points={
            'console_scripts':['tasksync = tasksync.sync:main']
        }
)
