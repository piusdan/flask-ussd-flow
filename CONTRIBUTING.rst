Contributing Guidelines
=======================


Questions, Feature Requests, Bug Reports, and Feedback…
-------------------------------------------------------

…should all be reported on the `Github Issue Tracker`_ .

.. _`Bitbucket Issue Tracker`: https://github.com/Piusdan/flask-ussd-flow/issues


Ways to Contribute
------------------

- If you think you've found a bug, open an issue.
- Send a PR for an open issue. The next section details how to contribute code.



Contributing Code
-----------------


In General
++++++++++

- `PEP 8`_, when sensible.
- Test ruthlessly. Write docs for new features.
- Even more important than Test-Driven Development--*Human-Driven Development*.

.. _`PEP 8`: http://www.python.org/dev/peps/pep-0008/

In Particular
+++++++++++++


Setting Up for Local Development
********************************

1. Fork on Github. ::

    $ git clone git@github.com:Piusdan/flask-ussd-flow.git

2. Install development requirements. It is highly recommended that you use a virtualenv. ::

    # After activating your virtualenv
    $ pip install -e .[dev] --upgrade

3. Install the pre-commit hooks, which will format and lint your git staged files. ::

    # The pre-commit CLI was installed above
    $ pre-commit install --allow-missing-config


Git Branch Structure
********************

Always use `Gitflow`_.

.. _`Gitflow`:  https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow


Pull Requests
**************

1. Create a new local branch.
::

    # For a new feature
    $ git checkout -b name-of-feature dev

    # For a bugfix
    $ git checkout -b fix-something 2.x-line

2. Commit your changes. Write `good commit messages <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.
::

    $ git commit -m "Detailed commit message"
    $ git push origin develop

4. Submit a pull request to the appropriate maintenance branch. 

Running tests
*************

Do: ::

    $ make test