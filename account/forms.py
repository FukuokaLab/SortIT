from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

# Get the User model
User = get_user_model()


class LoginForm(AuthenticationForm):
    # class for bootstrap4
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["placeholder"] = field.label  # placeholder


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "last_name",
            "first_name",
            "email",
            "username",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["required"] = ""

            if field.label == "Last Name":
                field.widget.attrs["autofocus"] = ""
                field.widget.attrs["placeholder"] = "Tanaka"
            elif field.label == "First Name":
                field.widget.attrs["placeholder"] = "Ichiro"
            elif field.label == "E mail":
                field.widget.attrs["placeholder"] = "***@gmail.com"


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "last_name",
            "first_name",
            "email",
            "username",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["required"] = ""


class MyPasswordChangeForm(PasswordChangeForm):
    # class for bootstrap4
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
