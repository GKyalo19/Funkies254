from django.contrib.auth.tokens import PasswordResetTokenGenerator


class PasswordResetTokenGeneratorWithEmailSalt(PasswordResetTokenGenerator):
    """
    Default generator + one extra field (email) hashed into the token, so a
    reset link is invalidated the moment the email changes, on top of the
    default invalidation on password change / after expiry.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.password}{timestamp}{user.email}"


password_reset_token = PasswordResetTokenGeneratorWithEmailSalt()
