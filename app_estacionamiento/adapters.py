from allauth.account.adapter import DefaultAccountAdapter

class NoUsernameAccountAdapter(DefaultAccountAdapter):

    def generate_unique_username(self, txts, regex=None):
        return None

    def populate_username(self, request, user):
        # No usar username nunca
        return