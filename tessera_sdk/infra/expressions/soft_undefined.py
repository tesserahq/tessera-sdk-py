from jinja2 import Undefined


class SoftUndefined(Undefined):
    """
    Behaves like JavaScript/JSON undefined:
    - No exceptions
    - Propagates when accessed
    - Renders as empty string
    - == None for comparisons
    """

    def _fail_with_undefined_error(self, *args, **kwargs):
        # Override the error path → no exception
        return self

    # When cast to string
    def __str__(self):
        return ""

    def __repr__(self):
        return "None"

    # When used in math or filters, behave like None
    def __getattr__(self, name):
        return self

    def __getitem__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self
