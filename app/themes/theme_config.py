THEMES = {
    'dark': {
        'bg': 'bg-gray-900',
        'text': 'text-gray-100',
        'btn': 'bg-blue-600 hover:bg-blue-700',
        'input': 'bg-gray-800 border-gray-700',
        'navbar': 'bg-gray-800',
        'modal': 'bg-gray-800',
        'accent': 'text-blue-400'
    },
    'light': {
        'bg': 'bg-gray-100',
        'text': 'text-gray-900',
        'btn': 'bg-blue-500 hover:bg-blue-600',
        'input': 'bg-white border-gray-300',
        'navbar': 'bg-white',
        'modal': 'bg-white',
        'accent': 'text-blue-600'
    },
    'neon': {
        'bg': 'bg-black',
        'text': 'text-green-400',
        'btn': 'bg-purple-600 hover:bg-purple-700 shadow-lg shadow-purple-500/50',
        'input': 'bg-gray-900 border-purple-500',
        'navbar': 'bg-black border-b border-purple-500',
        'modal': 'bg-gray-900 border border-purple-500',
        'accent': 'text-purple-400'
    },
    'futurist': {
        'bg': 'bg-gradient-to-br from-gray-900 to-blue-900',
        'text': 'text-blue-100',
        'btn': 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700',
        'input': 'bg-gray-800/50 border-blue-500/50',
        'navbar': 'bg-gray-900/90 backdrop-blur-sm',
        'modal': 'bg-gray-900/95 backdrop-blur-md border border-blue-500/20',
        'accent': 'text-cyan-400'
    },
    'classic': {
        'bg': 'bg-white',
        'text': 'text-gray-800',
        'btn': 'bg-gray-800 hover:bg-gray-900',
        'input': 'bg-gray-50 border-gray-200',
        'navbar': 'bg-gray-100',
        'modal': 'bg-white',
        'accent': 'text-gray-600'
    }
}

def get_theme(name='futurist'):
    return THEMES.get(name, THEMES['futurist'])
