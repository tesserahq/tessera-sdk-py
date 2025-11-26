import pytest

from tessera_sdk.utils.expressions.engine import ExpressionEngine


@pytest.fixture
def engine():
    """Create an ExpressionEngine instance for testing."""
    return ExpressionEngine()


def test_render_simple_variable(engine):
    """Test rendering a simple variable."""
    template = "Hello {{ name }}"
    context = {"name": "World"}
    result = engine.render(template, context)
    assert result == "Hello World"


def test_render_multiple_variables(engine):
    """Test rendering multiple variables."""
    template = "{{ greeting }}, {{ name }}!"
    context = {"greeting": "Hello", "name": "World"}
    result = engine.render(template, context)
    assert result == "Hello, World!"


def test_render_missing_variable(engine):
    """Test that missing variables render as empty string."""
    template = "Hello {{ missing }}"
    context = {}
    result = engine.render(template, context)
    assert result == "Hello "


def test_render_multiple_missing_variables(engine):
    """Test that multiple missing variables all render as empty strings."""
    template = "{{ a }}{{ b }}{{ c }}"
    context = {}
    result = engine.render(template, context)
    assert result == ""


def test_render_nested_variable(engine):
    """Test rendering nested variables from context."""
    template = "{{ json.name }}"
    context = {"json": {"name": "test"}}
    result = engine.render(template, context)
    assert result == "test"


def test_render_deeply_nested_variable(engine):
    """Test rendering deeply nested variables."""
    template = "{{ node.Trigger.json.data }}"
    context = {"node": {"Trigger": {"json": {"data": "value"}}}}
    result = engine.render(template, context)
    assert result == "value"


def test_render_missing_nested_variable(engine):
    """Test that missing nested variables render as empty string."""
    template = "{{ json.missing }}"
    context = {"json": {"name": "test"}}
    result = engine.render(template, context)
    assert result == ""


def test_render_upper_filter(engine):
    """Test the upper filter."""
    template = "{{ name | upper }}"
    context = {"name": "hello"}
    result = engine.render(template, context)
    assert result == "HELLO"


def test_render_upper_filter_non_string(engine):
    """Test that upper filter handles non-string values."""
    template = "{{ number | upper }}"
    context = {"number": 123}
    result = engine.render(template, context)
    assert result == "123"


def test_render_default_filter_with_none(engine):
    """Test default filter with None value."""
    template = "{{ value | default('N/A') }}"
    context = {"value": None}
    result = engine.render(template, context)
    assert result == "N/A"


def test_render_default_filter_with_empty_string(engine):
    """Test default filter with empty string."""
    template = "{{ value | default('N/A') }}"
    context = {"value": ""}
    result = engine.render(template, context)
    assert result == "N/A"


def test_render_default_filter_with_missing_variable(engine):
    """Test default filter with missing variable."""
    template = "{{ missing | default('N/A') }}"
    context = {}
    result = engine.render(template, context)
    assert result == "N/A"


def test_render_default_filter_with_value(engine):
    """Test default filter when value exists."""
    template = "{{ value | default('N/A') }}"
    context = {"value": "actual"}
    result = engine.render(template, context)
    assert result == "actual"


def test_render_default_filter_no_default_value(engine):
    """Test default filter without specifying default value."""
    template = "{{ missing | default }}"
    context = {}
    result = engine.render(template, context)
    assert result == ""


def test_render_complex_context(engine):
    """Test rendering with complex context structure."""
    template = "{{ json.name }} from {{ env.BASE_URL }} via {{ node.Trigger.json.id }}"
    context = {
        "json": {"name": "test"},
        "env": {"BASE_URL": "https://api.example.com"},
        "node": {"Trigger": {"json": {"id": "123"}}},
    }
    result = engine.render(template, context)
    assert result == "test from https://api.example.com via 123"


def test_render_with_numbers(engine):
    """Test rendering numeric values."""
    template = "Count: {{ count }}"
    context = {"count": 42}
    result = engine.render(template, context)
    assert result == "Count: 42"


def test_render_with_boolean(engine):
    """Test rendering boolean values."""
    template = "Active: {{ active }}"
    context = {"active": True}
    result = engine.render(template, context)
    assert result == "Active: True"


def test_render_empty_template(engine):
    """Test rendering an empty template."""
    template = ""
    context = {}
    result = engine.render(template, context)
    assert result == ""


def test_render_template_with_no_variables(engine):
    """Test rendering a template with no variables."""
    template = "Static text"
    context = {}
    result = engine.render(template, context)
    assert result == "Static text"


def test_render_with_list_access(engine):
    """Test rendering with list index access."""
    template = "First: {{ items[0] }}"
    context = {"items": ["a", "b", "c"]}
    result = engine.render(template, context)
    assert result == "First: a"


def test_render_with_missing_list_index(engine):
    """Test rendering with missing list index."""
    template = "Missing: {{ items[10] }}"
    context = {"items": ["a", "b", "c"]}
    result = engine.render(template, context)
    assert result == "Missing: "


def test_render_combined_filters(engine):
    """Test combining multiple filters."""
    template = "{{ name | upper | default('UNKNOWN') }}"
    context = {"name": "hello"}
    result = engine.render(template, context)
    assert result == "HELLO"


def test_render_combined_filters_with_missing(engine):
    """Test combining filters with missing variable."""
    template = "{{ missing | upper | default('UNKNOWN') }}"
    context = {}
    result = engine.render(template, context)
    assert result == "UNKNOWN"


def test_render_with_jinja2_conditionals(engine):
    """Test rendering with Jinja2 conditionals."""
    template = "{% if active %}Yes{% else %}No{% endif %}"
    context = {"active": True}
    result = engine.render(template, context)
    assert result == "Yes"


def test_render_with_jinja2_loops(engine):
    """Test rendering with Jinja2 loops."""
    template = "{% for item in items %}{{ item }}{% endfor %}"
    context = {"items": ["a", "b", "c"]}
    result = engine.render(template, context)
    assert result == "abc"


def test_render_autoescape_disabled(engine):
    """Test that autoescape is disabled (HTML not escaped)."""
    template = "{{ html }}"
    context = {"html": "<script>alert('xss')</script>"}
    result = engine.render(template, context)
    assert result == "<script>alert('xss')</script>"


def test_render_with_special_characters(engine):
    """Test rendering with special characters."""
    template = "{{ text }}"
    context = {"text": "Hello & World < > \" '"}
    result = engine.render(template, context)
    assert result == "Hello & World < > \" '"
