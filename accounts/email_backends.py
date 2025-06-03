# accounts/email_backends.py
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

class DebugEmailBackend(ConsoleEmailBackend):
    """
    Backend qui affiche également les détails importants des URLs
    dans les emails de réinitialisation de mot de passe.
    """
    def send_messages(self, messages):
        for message in messages:
            if "reset" in message.subject.lower():
                print("\n" + "="*80)
                print("LIEN DE RÉINITIALISATION EXTRAIT:")
                print(message.body)
                print("="*80 + "\n")
        
        return super().send_messages(messages)