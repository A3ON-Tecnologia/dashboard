from jinja2 import Environment, FileSystemLoader
import os

# Configure Jinja environment
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'templates'))
env = Environment(loader=FileSystemLoader(template_dir))

# Test theme data
theme = {
    'accent': 'text-blue-500',
    'btn': 'bg-blue-500',
    'modal': 'bg-gray-800',
    'bg': 'bg-gray-900',
    'text': 'text-white'
}

try:
    # Try to load and render home template
    template = env.get_template('home.html')
    output = template.render(theme=theme, current_user={'is_authenticated': False})
    print("Template rendered successfully!")
except Exception as e:
    print(f"Error rendering template: {str(e)}")
