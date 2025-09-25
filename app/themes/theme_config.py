THEMES = {
    'dark': {
        'bg': 'bg-gray-900',
        'text': 'text-gray-100',
        'btn': 'bg-blue-600 hover:bg-blue-700',
        'input': 'bg-gray-700 border-gray-600 text-white placeholder-gray-400',
        'navbar': 'bg-gray-800',
        'modal': 'bg-gray-800',
        'accent': 'text-blue-400'
    },
    'light': {
        'bg': 'bg-gray-100',
        'text': 'text-gray-900',
        'btn': 'bg-blue-500 hover:bg-blue-600',
        'input': 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-500',
        'navbar': 'bg-white',
        'modal': 'bg-white',
        'accent': 'text-blue-600'
    },
    'neon': {
        'bg': 'bg-black',
        'text': 'text-green-400',
        'btn': 'bg-purple-600 hover:bg-purple-700 shadow-lg shadow-purple-500/50',
        'input': 'bg-gray-800 border-purple-500 text-green-200 placeholder-purple-300/70',
        'navbar': 'bg-black border-b border-purple-500',
        'modal': 'bg-gray-900 border border-purple-500',
        'accent': 'text-purple-400'
    },
    'futurist': {
        'bg': 'bg-gradient-to-br from-gray-900 to-blue-900',
        'text': 'text-blue-100',
        'btn': 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700',
        'input': 'bg-gray-800/50 border-blue-500/50',
        'navbar': 'bg-gray-900 border-b border-blue-500/20',
        'modal': 'bg-gray-900/95',
        'accent': 'text-cyan-400'
    }
}

def get_theme(name='futurist'):
    return THEMES.get(name, THEMES['futurist'])
