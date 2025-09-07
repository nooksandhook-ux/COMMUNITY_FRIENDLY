from flask import request, url_for

def generate_breadcrumbs():
    """
    Dynamically generate breadcrumb items based on the current request endpoint.
    Returns HTML string for breadcrumb items to be inserted after the Home breadcrumb.
    """
    # Define breadcrumb configurations
    breadcrumb_config = {
        'dashboard.index': [('Dashboard', None)],
        'nook.index': [('Nook', None)],
        'nook.read': [('Nook', 'nook.index'), ('Read', None)],
        'nook.add_book': [('Nook', 'nook.index'), ('Add Book', None)],
        'nook.search_books': [('Nook', 'nook.index'), ('Search Books', None)],
        'nook.book': [('Nook', 'nook.index'), ('Book Details', None)],
        'nook.library': [('Nook', 'nook.index'), ('Library', None)],
        'nook.analytics': [('Nook', 'nook.index'), ('Analytics', None)],
        'hook.index': [('Hook', None)],
        'hook.timer': [('Hook', 'hook.index'), ('Focus Timer', None)],
        'hook.history': [('Hook', 'hook.index'), ('History', None)],
        'hook.analytics': [('Hook', 'hook.index'), ('Analytics', None)],
        'rewards.index': [('Rewards', None)],
        'rewards.history': [('Rewards', 'rewards.index'), ('History', None)],
        'rewards.badges': [('Rewards', 'rewards.index'), ('Badges', None)],
        'rewards.leaderboard': [('Rewards', 'rewards.index'), ('Leaderboard', None)],
        'rewards.analytics': [('Rewards', 'rewards.index'), ('Analytics', None)],
        'quotes.index': [('Quotes', None)],
        'quotes.submit': [('Quotes', 'quotes.index'), ('Submit Quote', None)],
        'quotes.admin.pending': [('Quotes', 'quotes.index'), ('Pending Quotes', None)],
        'nooks_club.index': [('Nooks Club', None)],
        'nooks_club.create': [('Nooks Club', 'nooks_club.index'), ('Create Club', None)],
        'nooks_club.club': [('Nooks Club', 'nooks_club.index'), ('Club Details', None)],
        'nooks_club.chat': [('Nooks Club', 'nooks_club.index'), ('Chat', None)],
        'mini_modules.flashcards': [('Flashcards', None)],
        'mini_modules.quiz': [('Quiz', None)],
        'mini_modules.quiz.leaderboard': [('Quiz', 'mini_modules.quiz'), ('Leaderboard', None)],
        'mini_modules.quiz.analytics': [('Quiz', 'mini_modules.quiz'), ('Analytics', None)],
        'donations.donate': [('Donations', None)],
        'donations.transactions': [('Donations', 'donations.donate'), ('Transactions', None)],
        'donations.sponsorship': [('Donations', 'donations.donate'), ('Sponsorship', None)],
        'analytics.transparency': [('Analytics', None)],
        'analytics.impact': [('Analytics', 'analytics.transparency'), ('Impact', None)],
        'auth.profile': [('Profile', None)],
        'auth.settings': [('Settings', None)],
        'auth.change_password': [('Settings', 'auth.settings'), ('Change Password', None)],
        'themes.index': [('Themes', None)],
        'themes.customize': [('Themes', 'themes.index'), ('Customize', None)],
        'admin.index': [('Admin', None)],
        'admin.users': [('Admin', 'admin.index'), ('Users', None)],
        'admin.analytics': [('Admin', 'admin.index'), ('Analytics', None)],
        'admin.content': [('Admin', 'admin.index'), ('Content', None)],
        'admin.rewards': [('Admin', 'admin.index'), ('Rewards', None)],
        'general.about': [('About', None)],
        'general.contact': [('Contact', None)],
        'general.privacy': [('Privacy Policy', None)],
        'general.terms': [('Terms of Service', None)],
        'general.fair_use': [('Fair Use', None)],
    }

    endpoint = request.endpoint
    breadcrumbs = breadcrumb_config.get(endpoint, [(endpoint.replace('.', ' ').title(), None)])

    html = ''
    for label, endpoint_url in breadcrumbs:
        if endpoint_url:
            html += f'<li class="breadcrumb-item"><a href="{url_for(endpoint_url)}">{label}</a></li>'
        else:
            html += f'<li class="breadcrumb-item active" aria-current="page">{label}</li>'
    
    return html

def register_breadcrumbs(app):
    """
    Register the generate_breadcrumbs function as a Jinja2 global.
    """
    app.jinja_env.globals['generate_breadcrumbs'] = generate_breadcrumbs
